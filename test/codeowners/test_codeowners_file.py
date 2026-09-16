import unittest

from src.codeowners.codeowners_file import (
    owners_of,
    owning_rule,
    parse_codeowners,
)

# The example file from GitHub's CODEOWNERS documentation, comments trimmed.
GITHUB_DOC_EXAMPLE = """
*       @global-owner1 @global-owner2

*.js    @js-owner #This is an inline comment.

*.go docs@example.com

*.txt @octo-org/octocats

/build/logs/ @doctocat

docs/*  @doctocat

apps/ @octocat

/docs/ @doctocat

/scripts/ @doctocat @octocat

**/logs @octocat

/apps/ @octocat
/apps/github
"""


class TestGithubDocExamples(unittest.TestCase):
    def setUp(self):
        self.rules = parse_codeowners(GITHUB_DOC_EXAMPLE)

    def owners(self, path):
        return list(owners_of(self.rules, path))

    def test_star_is_default(self):
        self.assertEqual(self.owners("README.md"), ["@global-owner1", "@global-owner2"])

    def test_extension_anywhere_and_inline_comment_stripped(self):
        self.assertEqual(self.owners("src/deep/x.js"), ["@js-owner"])

    def test_email_owner_is_kept_verbatim(self):
        self.assertEqual(self.owners("main.go"), ["docs@example.com"])

    def test_team_owner(self):
        self.assertEqual(self.owners("notes/a.txt"), ["@octo-org/octocats"])
        rule = owning_rule(self.rules, "notes/a.txt")
        assert rule is not None
        self.assertEqual(rule.team_slugs(), ["octo-org/octocats"])
        self.assertEqual(rule.individual_logins(), [])

    def test_root_anchored_directory(self):
        build_logs = next(r for r in self.rules if r.pattern == "/build/logs/")
        self.assertTrue(build_logs.matches("build/logs/2024/out.log"))
        self.assertFalse(build_logs.matches("x/build/logs/out.log"))
        self.assertFalse(build_logs.matches("build/logs"))
        # `**/logs @octocat` comes later in the file, so it wins for build/logs too.
        self.assertEqual(self.owners("build/logs/2024/out.log"), ["@octocat"])
        self.assertEqual(self.owners("x/build/logs/out.log"), ["@octocat"])

    def test_docs_star_matches_direct_children_only(self):
        self.assertEqual(self.owners("docs/getting-started.md"), ["@doctocat"])
        docs_star = next(r for r in self.rules if r.pattern == "docs/*")
        self.assertFalse(docs_star.matches("docs/build-app/troubleshooting.md"))
        self.assertTrue(docs_star.matches("docs/getting-started.md"))

    def test_unanchored_directory_matches_anywhere(self):
        apps_rule = next(r for r in self.rules if r.pattern == "apps/")
        self.assertTrue(apps_rule.matches("apps/a.py"))
        self.assertTrue(apps_rule.matches("x/y/apps/a.py"))
        self.assertFalse(apps_rule.matches("x/y/apps"))

    def test_double_star_prefix(self):
        self.assertEqual(self.owners("deeply/nested/logs/x"), ["@octocat"])
        self.assertEqual(self.owners("logs/x"), ["@octocat"])

    def test_last_match_wins_and_empty_owners_clear(self):
        self.assertEqual(self.owners("apps/foo.py"), ["@octocat"])
        self.assertEqual(self.owners("apps/github/foo.py"), [])
        self.assertEqual(self.owners("apps/github"), [])
        self.assertIsNotNone(owning_rule(self.rules, "apps/github/foo.py"))

    def test_unowned_path_has_no_rule(self):
        rules = parse_codeowners("/only/this/ @a\n")
        self.assertIsNone(owning_rule(rules, "elsewhere/file"))
        self.assertEqual(owners_of(rules, "elsewhere/file"), ())


# A representative slice of Asana's codez CODEOWNERS file.
CODEZ_SNIPPET = """
/CODEOWNERS @Asana/security-development-team-workday-sync
/.github/CODEOWNERS @Asana/security-development-team-workday-sync
/asana2/asana/tools/aws_lambda/safe_pr_auto_approver/ @Asana/security-development-team-workday-sync
/.github/workflows/databricks_* @Asana/data-infrastructure-area-workday-sync
/asana2/asana/tools/terraform/modules/cell/ @Asana/platform-area-workday-sync @Asana/security-development-team-workday-sync @Asana/ci-cd-team-workday-sync
/asana2/asana/tools/terraform/general/github-enterprise/ @harshita-gupta @ericrafalovsky @Asana/security-development-team-workday-sync
/.codex/rules/* @Asana/ai-dev-experience-team-workday-sync @Asana/dev-tooling-team-workday-sync
apps/asana/model/language_model/interactions/automations/resolve_automation_llm_interaction_prompts.ts @Asana/rules-platform-team-workday-sync @Asana/rules-experience-team-workday-sync
"""


class TestCodezPatterns(unittest.TestCase):
    def setUp(self):
        self.rules = parse_codeowners(CODEZ_SNIPPET)

    def owners(self, path):
        return list(owners_of(self.rules, path))

    def test_root_file(self):
        self.assertEqual(
            self.owners("CODEOWNERS"), ["@Asana/security-development-team-workday-sync"]
        )
        self.assertEqual(self.owners("some/dir/CODEOWNERS"), [])

    def test_anchored_directory(self):
        self.assertEqual(
            self.owners("asana2/asana/tools/aws_lambda/safe_pr_auto_approver/main.go"),
            ["@Asana/security-development-team-workday-sync"],
        )
        self.assertEqual(self.owners("asana2/asana/tools/aws_lambda/other/main.go"), [])
        # cell_kubernetes_resources is not modules/cell/
        self.assertEqual(
            self.owners(
                "asana2/asana/tools/terraform/modules/cell_kubernetes_resources/x.tf"
            ),
            [],
        )
        self.assertEqual(
            len(self.owners("asana2/asana/tools/terraform/modules/cell/main.tf")), 3
        )

    def test_glob_in_filename(self):
        self.assertEqual(
            self.owners(".github/workflows/databricks_nightly.yml"),
            ["@Asana/data-infrastructure-area-workday-sync"],
        )
        self.assertEqual(self.owners(".github/workflows/other_databricks_x.yml"), [])

    def test_anchored_without_leading_slash(self):
        self.assertEqual(
            self.owners(".codex/rules/foo.md"),
            [
                "@Asana/ai-dev-experience-team-workday-sync",
                "@Asana/dev-tooling-team-workday-sync",
            ],
        )
        self.assertEqual(self.owners(".codex/rules/nested/foo.md"), [])
        self.assertEqual(self.owners("x/.codex/rules/foo.md"), [])
        self.assertEqual(
            len(
                self.owners(
                    "apps/asana/model/language_model/interactions/automations/"
                    "resolve_automation_llm_interaction_prompts.ts"
                )
            ),
            2,
        )

    def test_individuals_and_team_on_one_line(self):
        rule = owning_rule(
            self.rules, "asana2/asana/tools/terraform/general/github-enterprise/main.tf"
        )
        assert rule is not None
        self.assertEqual(
            rule.team_slugs(), ["Asana/security-development-team-workday-sync"]
        )
        self.assertEqual(rule.individual_logins(), ["harshita-gupta", "ericrafalovsky"])


class TestSyntaxEdgeCases(unittest.TestCase):
    def test_escaped_space_in_pattern(self):
        rules = parse_codeowners("/docs/my\\ file.md @o")
        self.assertEqual(rules[0].pattern, "/docs/my file.md")
        self.assertEqual(rules[0].owners, ("@o",))
        self.assertEqual(owners_of(rules, "docs/my file.md"), ("@o",))

    def test_inline_comment_after_tab(self):
        rules = parse_codeowners("*.js\t@js-owner\t#tab comment here")
        self.assertEqual(rules[0].owners, ("@js-owner",))

    def test_hash_inside_a_token_is_not_a_comment(self):
        rules = parse_codeowners("/c#/ @o")
        self.assertEqual(rules[0].pattern, "/c#/")

    def test_line_with_an_invalid_owner_is_skipped(self):
        rules = parse_codeowners("/a/ @o\n/b/ bob\n/c/ @Asana/team not-an-owner\n")
        self.assertEqual([r.pattern for r in rules], ["/a/"])
        self.assertEqual(owners_of(rules, "b/x"), ())

    def test_emails_and_teams_are_valid_owners(self):
        rules = parse_codeowners("/a/ docs@example.com @octo-org/octocats @octocat")
        self.assertEqual(len(rules), 1)

    def test_bare_slash_owns_nothing(self):
        rules = parse_codeowners("/ @x\n/src/ @y")
        self.assertEqual(owners_of(rules, "README.md"), ())
        self.assertEqual(owners_of(rules, "src/a.py"), ("@y",))


if __name__ == "__main__":
    unittest.main()
