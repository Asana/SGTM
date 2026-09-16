from datetime import datetime, timezone
from unittest.mock import patch

from src.codeowners.codeowners_file import parse_codeowners
from src.codeowners.requirements import OwnerSet, requirements_for_files
from src.codeowners.status import (
    RequirementEvaluation,
    REVIEW_STATUS_NEEDS_CODEOWNER_APPROVAL,
    CodeownerSummary,
    FileStatus,
    ParentCodeownerStatus,
    RequirementStatus,
    aggregate_parent_status,
    evaluate_requirement,
    has_primary_review,
    review_status,
)
from src.github.models import ReviewState
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build

SECDEV = "@Asana/secdev"
PLATFORM = "@Asana/platform"
CICD = "@Asana/cicd"
SECDEV_MEMBERS = {"jordan", "eli", "pete"}
PLATFORM_MEMBERS = {"thelma", "vignir", "nicanor"}
CICD_MEMBERS = {"dharmesh", "fangjian"}
TEAM_MEMBERS = {
    "Asana/secdev": SECDEV_MEMBERS,
    "Asana/platform": PLATFORM_MEMBERS,
    "Asana/cicd": CICD_MEMBERS,
}

CODEOWNERS = f"""
/lambda/auto_approver/ {SECDEV}
/modules/cell/ {PLATFORM} {SECDEV} {CICD}
"""
AUTO_APPROVER = "lambda/auto_approver/config.yaml"
CELL_DATA = "modules/cell/data.tf"
CELL_LOCALS = "modules/cell/locals.tf"


def resolve_pool(owner_set: OwnerSet):
    logins = set(owner_set.individual_logins())
    for slug in owner_set.team_slugs():
        logins |= TEAM_MEMBERS[slug]
    return logins


def t(hour, day=14):
    return datetime(2026, 9, day, hour, 0, tzinfo=timezone.utc)


def review(login, state, when, commit="abc"):
    return build(
        builder.review()
        .author(builder.user(login))
        .state(state)
        .submitted_at(when)
        .commit_oid(commit)
    )


def requirement_for(*files):
    rules = parse_codeowners(CODEOWNERS)
    requirements = requirements_for_files(rules, list(files))
    assert len(requirements) == 1, requirements
    return requirements[0]


class TestEvaluateRequirement(BaseClass):
    def test_no_reviews_is_needed(self):
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, [], "author"
        )
        self.assertIs(evaluation.status, RequirementStatus.NEEDED)
        self.assertTrue(evaluation.is_outstanding())
        self.assertIsNone(evaluation.approval_review())

    def test_member_approval_is_approved(self):
        reviews = [review("jordan", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "author"
        )
        self.assertIs(evaluation.status, RequirementStatus.APPROVED)
        self.assertTrue(evaluation.is_satisfied())
        approval = evaluation.approval_review()
        assert approval is not None
        self.assertEqual(approval.author_handle(), "jordan")

    def test_any_owner_on_a_shared_line_satisfies_the_file(self):
        # PR #436513: three teams co-own the cell files; one platform approval
        # satisfies the single requirement.
        reviews = [review("thelma", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(
            requirement_for(CELL_DATA, CELL_LOCALS), resolve_pool, reviews, "nicanor"
        )
        self.assertIs(evaluation.status, RequirementStatus.APPROVED)
        self.assertEqual(
            [f.status for f in evaluation.files], [FileStatus.APPROVED] * 2
        )

    def test_author_never_satisfies(self):
        reviews = [review("jordan", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "jordan"
        )
        self.assertIs(evaluation.status, RequirementStatus.NEEDED)

    def test_an_active_request_for_changes_blocks_whatever_the_order(self):
        requirement = requirement_for(AUTO_APPROVER)
        cr_last = [
            review("jordan", ReviewState.APPROVED, t(10)),
            review("eli", ReviewState.CHANGES_REQUESTED, t(11)),
        ]
        self.assertIs(
            evaluate_requirement(requirement, resolve_pool, cr_last, "author").status,
            RequirementStatus.CHANGES_REQUESTED,
        )
        # Another owner approving does not clear eli's request, as on GitHub.
        approval_last = [
            review("eli", ReviewState.CHANGES_REQUESTED, t(10)),
            review("jordan", ReviewState.APPROVED, t(11)),
        ]
        self.assertIs(
            evaluate_requirement(
                requirement, resolve_pool, approval_last, "author"
            ).status,
            RequirementStatus.CHANGES_REQUESTED,
        )
        # The same owner approving after their own request does.
        same_owner = [
            review("eli", ReviewState.CHANGES_REQUESTED, t(10)),
            review("eli", ReviewState.APPROVED, t(11)),
        ]
        self.assertIs(
            evaluate_requirement(
                requirement, resolve_pool, same_owner, "author"
            ).status,
            RequirementStatus.APPROVED,
        )

    def test_dismissed_approval_is_stale(self):
        reviews = [
            review("jordan", ReviewState.APPROVED, t(9)),
            review("jordan", ReviewState.DISMISSED, t(11)),
        ]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "author"
        )
        self.assertIs(evaluation.status, RequirementStatus.APPROVAL_STALE)
        stale = evaluation.stale_review()
        assert stale is not None
        self.assertEqual(stale.author_handle(), "jordan")

    def test_dismissed_review_does_not_hide_an_active_request_for_changes(self):
        reviews = [
            review("eli", ReviewState.CHANGES_REQUESTED, t(9)),
            review("jordan", ReviewState.APPROVED, t(10)),
            review("jordan", ReviewState.DISMISSED, t(11)),
        ]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "author"
        )
        self.assertIs(evaluation.status, RequirementStatus.CHANGES_REQUESTED)

    def test_logins_compare_case_insensitively(self):
        reviews = [review("JORDAN", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "Author"
        )
        self.assertIs(evaluation.status, RequirementStatus.APPROVED)
        own_pr = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "Jordan"
        )
        self.assertIs(own_pr.status, RequirementStatus.NEEDED)

    @patch("src.codeowners.status.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS", {"pete"})
    def test_followup_users_do_not_satisfy_requirements(self):
        reviews = [review("pete", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "author"
        )
        self.assertIs(evaluation.status, RequirementStatus.NEEDED)

    def test_non_owner_reviews_are_ignored(self):
        reviews = [review("dharmesh", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, reviews, "author"
        )
        self.assertIs(evaluation.status, RequirementStatus.NEEDED)

    def test_folded_file_is_satisfied_by_its_own_owners(self):
        # secdev owns the auto-approver config; the cell file folds into the
        # secdev requirement but any of its three teams can approve it.
        requirement = requirement_for(AUTO_APPROVER, CELL_DATA)
        reviews = [review("thelma", ReviewState.APPROVED, t(10))]
        evaluation = evaluate_requirement(requirement, resolve_pool, reviews, "author")
        by_path = {f.path: f for f in evaluation.files}
        self.assertIs(by_path[CELL_DATA].status, FileStatus.APPROVED)
        self.assertIs(by_path[AUTO_APPROVER].status, FileStatus.NEEDED)
        self.assertIs(evaluation.status, RequirementStatus.NEEDED)

    def test_merged_without_approval_is_bypass(self):
        evaluation = evaluate_requirement(
            requirement_for(AUTO_APPROVER), resolve_pool, [], "author", merged=True
        )
        self.assertIs(evaluation.status, RequirementStatus.MERGED_WITH_BYPASS)
        approved = evaluate_requirement(
            requirement_for(AUTO_APPROVER),
            resolve_pool,
            [review("jordan", ReviewState.APPROVED, t(10))],
            "author",
            merged=True,
        )
        self.assertIs(approved.status, RequirementStatus.APPROVED)


class TestParentStatus(BaseClass):
    def evaluation(self, status):
        return RequirementEvaluation(requirement_for(AUTO_APPROVER), status)

    def test_states(self):
        self.assertIs(
            aggregate_parent_status([], False, False),
            ParentCodeownerStatus.NOT_REQUIRED,
        )
        self.assertIs(
            aggregate_parent_status([], True, False),
            ParentCodeownerStatus.NOT_YET_REQUESTED,
        )
        self.assertIs(
            aggregate_parent_status(
                [self.evaluation(RequirementStatus.NO_LONGER_REQUIRED)], True, True
            ),
            ParentCodeownerStatus.NOT_REQUIRED,
        )
        self.assertIs(
            aggregate_parent_status(
                [self.evaluation(RequirementStatus.NEEDED)], True, True
            ),
            ParentCodeownerStatus.PENDING,
        )
        self.assertIs(
            aggregate_parent_status(
                [
                    self.evaluation(RequirementStatus.APPROVED),
                    self.evaluation(RequirementStatus.APPROVAL_STALE),
                ],
                True,
                True,
            ),
            ParentCodeownerStatus.PARTIALLY_APPROVED,
        )
        self.assertIs(
            aggregate_parent_status(
                [self.evaluation(RequirementStatus.APPROVED)], True, True
            ),
            ParentCodeownerStatus.APPROVED,
        )
        self.assertIs(
            aggregate_parent_status(
                [
                    self.evaluation(RequirementStatus.APPROVED),
                    self.evaluation(RequirementStatus.CHANGES_REQUESTED),
                ],
                True,
                True,
            ),
            ParentCodeownerStatus.CHANGES_REQUESTED,
        )


class TestPrimaryReviewAndReviewStatus(BaseClass):
    def summary(self, reviews, human_chosen=frozenset(), tasks_requested=True):
        requirement = requirement_for(AUTO_APPROVER)
        evaluation = evaluate_requirement(
            requirement, resolve_pool, reviews, "harshita"
        )
        return CodeownerSummary(
            evaluations=[evaluation],
            codeowned_files={AUTO_APPROVER: requirement.owner_set},
            tasks_requested=tasks_requested,
            codeowner_logins=set(SECDEV_MEMBERS),
            human_chosen_logins=set(human_chosen),
        )

    def pull_request(self, reviews, draft=False):
        return build(
            builder.pull_request()
            .author(builder.user("harshita"))
            .reviews(reviews)
            .isDraft(draft)
        )

    def test_non_codeowner_approval_is_primary(self):
        reviews = [review("dharmesh", ReviewState.APPROVED, t(10))]
        self.assertTrue(
            has_primary_review(self.pull_request(reviews), self.summary(reviews))
        )

    def test_codeowner_approval_is_not_primary_unless_author_chose_them(self):
        reviews = [review("jordan", ReviewState.APPROVED, t(10))]
        self.assertFalse(
            has_primary_review(self.pull_request(reviews), self.summary(reviews))
        )
        self.assertTrue(
            has_primary_review(
                self.pull_request(reviews),
                self.summary(reviews, human_chosen={"jordan"}),
            )
        )

    def test_dismissed_primary_approval_no_longer_counts(self):
        reviews = [review("dharmesh", ReviewState.DISMISSED, t(10))]
        self.assertFalse(
            has_primary_review(self.pull_request(reviews), self.summary(reviews))
        )

    @patch(
        "src.codeowners.status.SGTM_FEATURE__FOLLOWUP_REVIEW_GITHUB_USERS", {"autobot"}
    )
    def test_followup_users_never_count(self):
        reviews = [review("autobot", ReviewState.APPROVED, t(10))]
        self.assertFalse(
            has_primary_review(self.pull_request(reviews), self.summary(reviews))
        )

    def test_review_status_precedence(self):
        # Draft
        self.assertEqual(
            review_status(self.pull_request([], draft=True), self.summary([])),
            "Not Ready",
        )
        # Nothing yet
        self.assertEqual(
            review_status(self.pull_request([]), self.summary([])), "Needs Review"
        )
        # Codeowner approved, no primary review
        codeowner_only = [review("jordan", ReviewState.APPROVED, t(10))]
        self.assertEqual(
            review_status(
                self.pull_request(codeowner_only), self.summary(codeowner_only)
            ),
            "Needs Review",
        )
        # Primary review in, codeowner outstanding
        primary_only = [review("dharmesh", ReviewState.APPROVED, t(10))]
        self.assertEqual(
            review_status(self.pull_request(primary_only), self.summary(primary_only)),
            REVIEW_STATUS_NEEDS_CODEOWNER_APPROVAL,
        )
        # Both
        both = primary_only + codeowner_only
        self.assertEqual(
            review_status(self.pull_request(both), self.summary(both)), "Approved"
        )
        # Author-chosen codeowner covers both at once
        self.assertEqual(
            review_status(
                self.pull_request(codeowner_only),
                self.summary(codeowner_only, human_chosen={"jordan"}),
            ),
            "Approved",
        )
        # A later request for changes wins
        with_cr = both + [review("eli", ReviewState.CHANGES_REQUESTED, t(12))]
        self.assertEqual(
            review_status(self.pull_request(with_cr), self.summary(with_cr)),
            "Changes Requested",
        )

    def test_review_status_is_unchanged_until_the_label_is_added(self):
        # A codeowner GitHub auto-requested approves an unlabeled PR: today's
        # rule ("Approved") still applies.
        codeowner_only = [review("jordan", ReviewState.APPROVED, t(10))]
        self.assertEqual(
            review_status(
                self.pull_request(codeowner_only),
                self.summary(codeowner_only, tasks_requested=False),
            ),
            "Approved",
        )
        primary_only = [review("dharmesh", ReviewState.APPROVED, t(10))]
        self.assertEqual(
            review_status(
                self.pull_request(primary_only),
                self.summary(primary_only, tasks_requested=False),
            ),
            "Approved",
        )

    def test_review_status_without_codeowned_files_is_unchanged(self):
        approved = [review("dharmesh", ReviewState.APPROVED, t(10))]
        pull_request = self.pull_request(approved)
        self.assertEqual(review_status(pull_request, None), "Approved")
        empty_summary = CodeownerSummary([], {}, False, set())
        self.assertEqual(review_status(pull_request, empty_summary), "Approved")
        self.assertEqual(review_status(self.pull_request([]), None), "Needs Review")


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
