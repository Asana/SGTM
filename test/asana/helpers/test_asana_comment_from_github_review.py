import src.asana.helpers
from test.impl.builders import builder, build
from test.asana.helpers.base_class import BaseClass

"""
    Extracts the GitHub author and comments from a GitHub Review, and transforms them into
    a suitable html comment string for Asana. This will involve looking up the GitHub author in
    DynamoDb to determine the Asana domain user id of the review author and any @mentioned GitHub
    users.
"""


class TestAsanaCommentFromGitHubReview(BaseClass):

    @classmethod
    def setUpClass(cls):
        BaseClass.setUpClass()
        cls.insert_test_user_into_user_table("github_test_user_login", "TEST_USER_ASANA_DOMAIN_USER_ID")

    def test_none_causes_valueerror(self):
        with self.assertRaises(ValueError):
            src.asana.helpers.asana_comment_from_github_review(None)

    def test_includes_comment_text(self):
        github_review = build(
            builder.review().
            author(builder.user("github_unknown_user_login")).
            state("APPROVED").
            body("GITHUB_REVIEW_TEXT")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_comment, ["GITHUB_REVIEW_TEXT"])

    def test_includes_asana_review_author(self):
        github_review = build(
            builder.review().
            author(builder.user("github_test_user_login")).
            state("APPROVED").
            body("GITHUB_REVIEW_TEXT")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_comment, ["TEST_USER_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_review_author_gracefully(self):
        github_review = build(
            builder.review().
            author(builder.user("github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME")).
            state("APPROVED").
            body("GITHUB_REVIEW_TEXT")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_comment, ["github_unknown_user_login", "GITHUB_UNKNOWN_USER_NAME"])

    def test_handles_non_asana_review_author_that_has_no_name_gracefully(self):
        github_review = build(
            builder.review().
                author(builder.user("github_unknown_user_login")).
                state("APPROVED").
                body("GITHUB_REVIEW_TEXT")
        )
        asana_comment = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_comment, ["github_unknown_user_login"])

    def test_does_not_inject_unsafe_html(self):
        placeholder = "💣"
        github_placeholder_review = build(
            builder.review().
                author(builder.user("github_unknown_user_login")).
                state("APPROVED").
                body(placeholder)
        )
        asana_placeholder_review = src.asana.helpers.asana_comment_from_github_review(github_placeholder_review)
        unsafe_characters = ["&", "<", ">"]
        for unsafe_character in unsafe_characters:
            github_review = build(
                builder.review().
                    author(builder.user("github_unknown_user_login")).
                    state("APPROVED").
                    body(unsafe_character)
            )
            asana_review = src.asana.helpers.asana_comment_from_github_review(github_review)
            unexpected = asana_placeholder_review.replace(placeholder, unsafe_character)
            self.assertNotEqual(asana_review, unexpected, f"Expected the {unsafe_character} character to be escaped")

    def test_considers_double_quotes_safe_in_review_text(self):
        placeholder = "💣"
        github_placeholder_review = build(
            builder.review().
                author(builder.user("github_unknown_user_login")).
                state("APPROVED").
                body(placeholder)
        )
        asana_placeholder_review = src.asana.helpers.asana_comment_from_github_review(github_placeholder_review)
        safe_characters = ["\"", "'"]
        for safe_character in safe_characters:
            github_review = build(
                builder.review().
                    author(builder.user("github_unknown_user_login")).
                    state("APPROVED").
                    body(safe_character)
            )
            asana_review = src.asana.helpers.asana_comment_from_github_review(github_review)
            expected = asana_placeholder_review.replace(placeholder, safe_character)
            self.assertEqual(asana_review, expected, f"Did not expected the {safe_character} character to be escaped")

    def test_transforms_github_at_mentions_to_asana_at_mentions(self):
        github_review = build(
            builder.review().
                author(builder.user("github_unknown_user_login")).
                state("APPROVED").
                body("@github_test_user_login")
        )
        asana_review = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_review, ["TEST_USER_ASANA_DOMAIN_USER_ID"])

    def test_handles_non_asana_comment_at_mention_gracefully(self):
        github_review = build(
            builder.review().
                author(builder.user("github_unknown_user_login")).
                state("APPROVED").
                body("@github_unknown_user_login")
        )
        asana_review = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_review, ["@github_unknown_user_login"])

    def test_handles_at_sign_in_review_gracefully(self):
        github_review = build(
            builder.review().
                author(builder.user("github_unknown_user_login")).
                state("APPROVED").
                body("hello@world.asana.com")
        )
        asana_review = src.asana.helpers.asana_comment_from_github_review(github_review)
        self.assertContainsStrings(asana_review, ["hello@world.asana.com"])

        
if __name__ == '__main__':
    from unittest import main as run_tests
    run_tests()
