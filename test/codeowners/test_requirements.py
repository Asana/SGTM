import unittest

from src.codeowners.codeowners_file import parse_codeowners
from src.codeowners.requirements import (
    OwnerSet,
    codeowned_files,
    requirements_for_files,
)

SECDEV = "@Asana/security-development-team-workday-sync"
PLATFORM = "@Asana/platform-area-workday-sync"
CICD = "@Asana/ci-cd-team-workday-sync"
DATA_INFRA = "@Asana/data-infrastructure-area-workday-sync"

CODEOWNERS = f"""
/CODEOWNERS {SECDEV}
/asana2/asana/tools/aws_lambda/safe_pr_auto_approver/ {SECDEV}
/.github/workflows/databricks_* {DATA_INFRA}
/asana2/asana/tools/terraform/modules/cell/ {PLATFORM} {SECDEV} {CICD}
/asana2/asana/tools/terraform/general/github-enterprise/ @harshita-gupta @ericrafalovsky {SECDEV}
/secret/ @alice @bob
"""

CELL_DATA = "asana2/asana/tools/terraform/modules/cell/data.tf"
CELL_LOCALS = "asana2/asana/tools/terraform/modules/cell/locals.tf"
AUTO_APPROVER = "asana2/asana/tools/aws_lambda/safe_pr_auto_approver/config.yaml"
GH_ENTERPRISE = "asana2/asana/tools/terraform/general/github-enterprise/main.tf"
DATABRICKS = ".github/workflows/databricks_nightly.yml"


class TestOwnerSet(unittest.TestCase):
    def test_team_slugs_are_case_insensitive(self):
        owner_set = OwnerSet.of(["@Asana/SecDev", "@asana/secdev", "@JohnDoe"])
        self.assertEqual(owner_set.owners, ("@JohnDoe", "@asana/secdev"))
        self.assertEqual(owner_set, OwnerSet.of(["@asana/secdev", "@JohnDoe"]))
        self.assertEqual(owner_set.key(), "JohnDoe+asana/secdev")
        # The first spelling is kept for display and API calls.
        self.assertEqual(owner_set.team_slugs(), ["Asana/SecDev"])
        self.assertEqual(owner_set.display_names(), ["@JohnDoe", "SecDev"])

    def test_sorted_and_deduplicated(self):
        owner_set = OwnerSet.of([SECDEV, PLATFORM, SECDEV])
        self.assertEqual(owner_set.as_written(), (PLATFORM, SECDEV))

    def test_key_display_and_short_display(self):
        owner_set = OwnerSet.of([SECDEV, PLATFORM, "@harshita-gupta"])
        self.assertEqual(
            owner_set.key(),
            "asana/platform-area-workday-sync+asana/security-development-team-workday-sync+harshita-gupta",
        )
        # Raw tokens sort with the org prefix first, so teams precede individuals.
        self.assertEqual(
            owner_set.display(),
            "platform-area-workday-sync + security-development-team-workday-sync + @harshita-gupta",
        )
        self.assertEqual(
            owner_set.short_display(),
            "platform-area + security-development-team + @harshita-gupta",
        )
        self.assertEqual(
            owner_set.team_slugs(),
            [
                "Asana/platform-area-workday-sync",
                "Asana/security-development-team-workday-sync",
            ],
        )
        self.assertEqual(owner_set.individual_logins(), ["harshita-gupta"])

    def test_strict_superset(self):
        small = OwnerSet.of([SECDEV])
        big = OwnerSet.of([SECDEV, PLATFORM])
        self.assertTrue(big.is_strict_superset_of(small))
        self.assertFalse(small.is_strict_superset_of(big))
        self.assertFalse(big.is_strict_superset_of(big))


class TestRequirements(unittest.TestCase):
    def setUp(self):
        self.rules = parse_codeowners(CODEOWNERS)

    def test_codeowned_files_omits_unowned(self):
        owned = codeowned_files(self.rules, ["README.md", AUTO_APPROVER])
        self.assertEqual(list(owned), [AUTO_APPROVER])
        self.assertEqual(owned[AUTO_APPROVER], OwnerSet.of([SECDEV]))

    def test_one_requirement_per_owner_set(self):
        # PR #436513: two files, both co-owned by three teams -> one subtask.
        requirements = requirements_for_files(
            self.rules, [CELL_DATA, CELL_LOCALS, "x.md"]
        )
        self.assertEqual(len(requirements), 1)
        requirement = requirements[0]
        self.assertEqual(requirement.owner_set, OwnerSet.of([PLATFORM, SECDEV, CICD]))
        self.assertEqual(requirement.files, [CELL_DATA, CELL_LOCALS])
        self.assertEqual(requirement.covered_files, {})

    def test_non_overlapping_owners_get_separate_requirements(self):
        requirements = requirements_for_files(self.rules, [AUTO_APPROVER, DATABRICKS])
        self.assertEqual(
            [r.owner_set for r in requirements],
            [OwnerSet.of([DATA_INFRA]), OwnerSet.of([SECDEV])],
        )

    def test_superset_is_folded_into_subset(self):
        # secdev alone owns the auto-approver config; the cell module is owned by
        # secdev plus two other teams. A secdev approval covers both, so the cell
        # files ride along in the secdev subtask.
        requirements = requirements_for_files(self.rules, [CELL_DATA, AUTO_APPROVER])
        self.assertEqual(len(requirements), 1)
        requirement = requirements[0]
        self.assertEqual(requirement.owner_set, OwnerSet.of([SECDEV]))
        self.assertEqual(requirement.files, [AUTO_APPROVER])
        self.assertEqual(
            requirement.covered_files,
            {CELL_DATA: OwnerSet.of([PLATFORM, SECDEV, CICD])},
        )
        self.assertEqual(requirement.all_files(), [AUTO_APPROVER, CELL_DATA])
        self.assertEqual(
            requirement.owners_for_file(CELL_DATA),
            OwnerSet.of([PLATFORM, SECDEV, CICD]),
        )
        self.assertEqual(
            requirement.owners_for_file(AUTO_APPROVER), OwnerSet.of([SECDEV])
        )

    def test_folds_into_the_smallest_subset(self):
        # {secdev} < {secdev, harshita, eric} < ... the github-enterprise line
        # folds into the bare secdev line, not into another superset.
        requirements = requirements_for_files(
            self.rules, [GH_ENTERPRISE, AUTO_APPROVER, CELL_LOCALS]
        )
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].owner_set, OwnerSet.of([SECDEV]))
        self.assertEqual(
            sorted(requirements[0].covered_files), [GH_ENTERPRISE, CELL_LOCALS]
        )

    def test_individuals_only_line_forms_its_own_owner_set(self):
        requirements = requirements_for_files(self.rules, ["secret/x"])
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].owner_set, OwnerSet.of(["@alice", "@bob"]))
        self.assertEqual(requirements[0].owner_set.team_slugs(), [])
        self.assertEqual(
            requirements[0].owner_set.individual_logins(), ["alice", "bob"]
        )

    def test_no_codeowned_files_means_no_requirements(self):
        self.assertEqual(requirements_for_files(self.rules, ["README.md"]), [])


if __name__ == "__main__":
    unittest.main()
