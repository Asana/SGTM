from test.impl.base_test_case_class import BaseClass

from src.github.models import Review


class TestReview(BaseClass):
    def test_with_status_of_approved__is_just_comments_is_false(self):
        raw_review = {"state": "APPROVED", "body": ""}
        review = Review(raw_review)
        self.assertEqual(review.is_just_comments(), False)

    def test_with_status_of_changes_requested__is_just_comments_is_false(self):
        raw_review = {"state": "CHANGES_REQUESTED", "body": ""}
        review = Review(raw_review)
        self.assertEqual(review.is_just_comments(), False)

    def test_with_status_of_commented_and_empty_body__is_just_comments_is_true(self):
        raw_review = {"state": "COMMENTED", "body": ""}
        review = Review(raw_review)
        self.assertEqual(review.is_just_comments(), True)

    def test_with_status_of_commented_and_populated_body__is_just_comments_is_false(
        self,
    ):
        raw_review = {"state": "COMMENTED", "body": "Here's a body!"}
        review = Review(raw_review)
        self.assertEqual(review.is_just_comments(), False)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
