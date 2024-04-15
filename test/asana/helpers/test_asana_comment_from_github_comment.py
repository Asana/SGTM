from html import escape
from unittest.mock import MagicMock, patch
import src.asana.helpers
from test.impl.mock_dynamodb_test_case import MockDynamoDbTestCase
from test.impl.builders import builder, build
from test.test_utils import magic_mock_with_return_type_value


@patch(
    "src.dynamodb.client.get_asana_domain_user_id_from_github_handle",
    magic_mock_with_return_type_value(
        {"github_test_user_login": "TEST_USER_ASANA_DOMAIN_USER_ID"}
    ),
)
class TestAsanaCommentFromGitHubComment(MockDynamoDbTestCase):
    @classmethod
    def setUpClass(cls):
        MockDynamoDbTestCase.setUpClass()

    def test_includes_comment_text(
        self,
        _get_asana_domain_id_mock,
    ):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("GITHUB_COMMENT_TEXT")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["GITHUB_COMMENT_TEXT"])

    def test_transforms_urls_from_comment_tect(
        self,
        _get_asana_domain_id_mock,
    ):
        url = "https://www.foo.bar/?a=1&b=2"
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("Can you refer to the documentation at {}".format(url))
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(
            asana_comment, ['<a href="{}">{}</a>'.format(escape(url), url)]
        )

    def test_includes_asana_comment_author(
        self,
        _get_asana_domain_id_mock,
    ):
        github_comment = build(
            builder.comment().author(builder.user("github_test_user_login"))
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["TEST_USER_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_author_gracefully(
        self,
        _get_asana_domain_id_mock,
    ):
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

    def test_handles_non_asana_comment_author_that_has_no_name_gracefully(
        self,
        _get_asana_domain_id_mock,
    ):
        github_comment = build(
            builder.comment().author(builder.user("github_unknown_user_login"))
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["github_unknown_user_login"])

    def test_does_not_inject_unsafe_html(
        self,
        _get_asana_domain_id_mock,
    ):
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

    def test_considers_double_quotes_safe_in_comment_text(
        self,
        _get_asana_domain_id_mock,
    ):
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

    def test_transforms_github_at_mentions_to_asana_at_mentions(
        self,
        _get_asana_domain_id_mock,
    ):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("@github_test_user_login")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["TEST_USER_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_at_mention_gracefully(
        self,
        _get_asana_domain_id_mock,
    ):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("@github_unknown_user_login")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["@github_unknown_user_login"])

    def test_handles_at_sign_in_comment_gracefully(
        self,
        _get_asana_domain_id_mock,
    ):
        github_comment = build(
            builder.comment()
            .author(builder.user("github_unknown_user_login"))
            .body("hello@world.asana.com")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, ["hello@world.asana.com"])

    def test_includes_url_in_comment(
        self,
        _get_asana_domain_id_mock,
    ):
        url = "https://github.com/Asana/SGTM/pull/31#issuecomment-626850667"
        github_comment = build(builder.comment().url(url))
        asana_comment = src.asana.helpers.asana_comment_from_github_comment(
            github_comment
        )
        self.assertContainsStrings(asana_comment, [f'<A href="{url}">'])


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
