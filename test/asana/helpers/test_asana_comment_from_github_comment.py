import src.asana.helpers
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from test.impl.builders import builder, build


class TestAsanaCommentFromGitHubComment(MockDynamoDbTestCase):
    @classmethod
    def setUpClass(cls):
        MockDynamoDbTestCase.setUpClass()
        cls.test_data.insert_user_into_user_table(
            "github_test_user_login", "TEST_USER_ASANA_DOMAIN_USER_ID"
        )

    def test_includes_comment_text(self):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("GITHUB_COMMENT_TEXT")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["GITHUB_COMMENT_TEXT"])

    def test_includes_asana_comment_author(self):
        github_comment = build(
            builder.comment().author(builder.user("github_test_user_login"))
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["TEST_USER_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_author_gracefully(self):
        github_comment = build(
            builder.comment().author(
                builder.user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")
            )
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(
            asana_comment, ["github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME"]
        )

    def test_handles_non_asana_comment_author_that_has_no_name_gracefully(self):
        github_comment = build(
            builder.comment().author(builder.user("github_unknown_user_login"))
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["github_unknown_user_login"])

    def test_does_not_inject_unsafe_html(self):
        placeholder = "💣"
        github_placeholder_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body(placeholder)
        )
        asana_placeholder_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_placeholder_comment
        )
        unsafe_characters = ["&", "<", ">"]
        for unsafe_character in unsafe_characters:
            github_comment = build(
                builder.comment()
                .author(builder.user("github_unknown_user_login"))
                .body(unsafe_character)
            )
            asana_comment = src.asana.helpers.asana_comment_from_github_comment(
                github_comment
            )
            unexpected = asana_placeholder_comment.replace(
                placeholder, unsafe_character
            )
            self.assertNotEqual(
                asana_comment,
                unexpected,
                f"Expected the {unsafe_character} character to be escaped",
            )

    def test_considers_double_quotes_safe_in_comment_text(self):
        github_author = builder.user("github_unknown_user_login")
        placeholder = "💣"
        github_placeholder_comment = build(
            builder.comment().body(placeholder).author(github_author)
        )
        asana_placeholder_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_placeholder_comment
        )
        safe_characters = ['"', "'"]
        for safe_character in safe_characters:
            github_comment = build(
                builder.comment().body(safe_character).author(github_author)
            )
            asana_comment = src.asana.helpers.asana_comment_from_github_comment(
                github_comment
            )
            expected = asana_placeholder_comment.replace(placeholder, safe_character)
            self.assertEqual(
                asana_comment,
                expected,
                f"Did not expected the {safe_character} character to be escaped",
            )

    def test_transforms_github_at_mentions_to_asana_at_mentions(self):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("@github_test_user_login")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["TEST_USER_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_at_mention_gracefully(self):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("@github_unknown_user_login")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["@github_unknown_user_login"])

    def test_handles_at_sign_in_comment_gracefully(self):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("hello@world.asana.com")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["hello@world.asana.com"])

    def test_includes_url_in_comment(self):
        url = 'https://github.com/Asana/SGTM/pull/31#issuecomment-626850667'
        github_comment = build(
            builder.comment()
            .url(url)
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, [f'<A href="{url}">'])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
