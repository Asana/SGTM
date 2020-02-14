import src.asana.helpers
from test.asana.helpers.base_class import BaseClass
from test.asana.helpers.scaffolding_helpers import create_github_user, create_comment


class TestAsanaCommentFromGitHubComment(BaseClass):

    def test_handles_illegal_args_gracefully(self):
        with self.assertRaises(ValueError):
            src.asana.helpers.asana_comment_from_github_comment(None)

    def test_includes_comment_text(self):
        github_comment = create_comment(body="GITHUB_COMMENT_TEXT")
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["GITHUB_COMMENT_TEXT"])

    def test_includes_asana_comment_author(self):
        github_author = create_github_user("github_author_login")
        github_comment = create_comment(with_author=github_author)
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["AUTHOR_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_author_gracefully(self):
        github_author = create_github_user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")
        github_comment = create_comment(with_author=github_author)
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME"])

    def test_handles_non_asana_comment_author_that_has_no_name_gracefully(self):
        github_author = create_github_user("github_unknown_user_login")
        github_comment = create_comment(with_author=github_author)
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["github_unknown_user_login"])

    def test_does_not_inject_unsafe_html(self):
        placeholder = "💣"
        github_placeholder_comment = create_comment(body=placeholder)
        asana_placeholder_comment = src.asana.helpers.asana_comment_from_github_comment(github_placeholder_comment)
        unsafe_characters = ["&", "<", ">"]
        for unsafe_character in unsafe_characters:
            github_comment = create_comment(body=unsafe_character)
            asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
            unexpected = asana_placeholder_comment.replace(placeholder, unsafe_character)
            self.assertNotEqual(asana_comment, unexpected, f"Expected the {unsafe_character} character to be escaped")

    def test_considers_double_quotes_safe_in_comment_text(self):
        placeholder = "💣"
        github_placeholder_comment = create_comment(body=placeholder)
        asana_placeholder_comment = src.asana.helpers.asana_comment_from_github_comment(github_placeholder_comment)
        safe_characters = ["\"", "'"]
        for safe_character in safe_characters:
            github_comment = create_comment(body=safe_character)
            asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
            expected = asana_placeholder_comment.replace(placeholder, safe_character)
            self.assertEqual(asana_comment, expected, f"Did not expected the {safe_character} character to be escaped")

    def test_transforms_github_at_mentions_to_asana_at_mentions(self):
        github_comment = create_comment(body="@github_author_login")
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["AUTHOR_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_at_mention_gracefully(self):
        github_comment = create_comment(body="@github_unknown_user_login")
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["@github_unknown_user_login"])

    def test_handles_at_sign_in_comment_gracefully(self):
        github_comment = create_comment(body="hello@world.asana.com")
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(github_comment)
        self.assertContainsStrings(asana_comment, ["hello@world.asana.com"])


if __name__ == '__main__':
    from unittest import main as run_tests
    run_tests()
