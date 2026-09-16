from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


class TestReviewRequests(BaseClass):
    def test_human_and_codeowner_requests_are_told_apart(self):
        human = build(builder.user().login("human-pick"))
        pull_request = build(
            builder.pull_request()
            .requested_reviewer(human)
            .requested_reviewer_team(
                "secdev",
                ["alice", "bob"],
                combined_slug="Asana/secdev",
                as_code_owner=True,
            )
        )
        requests = pull_request.review_requests()
        self.assertEqual(len(requests), 2)
        self.assertFalse(requests[0].as_code_owner())
        self.assertEqual(requests[0].login(), "human-pick")
        self.assertTrue(requests[1].as_code_owner())
        self.assertTrue(requests[1].is_team())
        self.assertEqual(requests[1].team_slug(), "Asana/secdev")
        self.assertEqual(requests[1].team_member_logins(), ["alice", "bob"])

        self.assertEqual(pull_request.human_requested_reviewer_logins(), ["human-pick"])
        self.assertEqual(
            pull_request.codeowner_requested_team_slugs(), ["Asana/secdev"]
        )

    def test_requested_reviewers_can_exclude_codeowner_requests(self):
        human = build(builder.user().login("human-pick"))
        pull_request = build(
            builder.pull_request()
            .requested_reviewer(human)
            .requested_reviewer_team("secdev", ["alice", "bob"], as_code_owner=True)
        )
        self.assertEqual(
            pull_request.requested_reviewers(), ["alice", "bob", "human-pick"]
        )
        self.assertEqual(
            pull_request.requested_reviewers(include_codeowner_requests=False),
            ["human-pick"],
        )

    def test_team_requested_by_a_human_still_counts_for_followers(self):
        pull_request = build(
            builder.pull_request().requested_reviewer_team("platform", ["carol"])
        )
        self.assertEqual(
            pull_request.requested_reviewers(include_codeowner_requests=False),
            ["carol"],
        )
        self.assertEqual(pull_request.codeowner_requested_team_slugs(), [])


class TestChangedFilesAndRefs(BaseClass):
    def test_changed_files_and_pagination_flags(self):
        pull_request = build(
            builder.pull_request().files(["a.py", "b/c.tf"], True, "cursor-1")
        )
        self.assertEqual(pull_request.changed_files(), ["a.py", "b/c.tf"])
        self.assertTrue(pull_request.has_unloaded_changed_files())
        self.assertEqual(pull_request.changed_files_end_cursor(), "cursor-1")

        pull_request.set_changed_files(["a.py", "b/c.tf", "d.md"])
        self.assertEqual(pull_request.changed_files(), ["a.py", "b/c.tf", "d.md"])
        self.assertFalse(pull_request.has_unloaded_changed_files())
        self.assertIsNone(pull_request.changed_files_end_cursor())

    def test_refs_and_stack(self):
        pull_request = build(
            builder.pull_request()
            .base_ref_name("feature/parent")
            .head_ref_oid("abc123")
            .stack_base_ref_name("next-master")
        )
        self.assertEqual(pull_request.base_ref_name(), "feature/parent")
        self.assertEqual(pull_request.head_ref_oid(), "abc123")
        self.assertTrue(pull_request.is_in_native_stack())
        self.assertEqual(pull_request.stack_base_ref_name(), "next-master")

        plain = build(builder.pull_request())
        self.assertFalse(plain.is_in_native_stack())
        self.assertIsNone(plain.stack_base_ref_name())
        self.assertEqual(plain.base_ref_name(), "master")

    def test_latest_commit_oid_and_date(self):
        commit = builder.commit().oid("deadbeef").committed_date("2026-09-11T02:00:00Z")
        pull_request = build(builder.pull_request().commit(commit))
        latest = pull_request.latest_commit()
        assert latest is not None
        self.assertEqual(latest.oid(), "deadbeef")
        committed_date = latest.committed_date()
        assert committed_date is not None
        self.assertEqual(committed_date.year, 2026)

    def test_review_commit_oid(self):
        review = build(builder.review().commit_oid("dd2fa868"))
        self.assertEqual(review.commit_oid(), "dd2fa868")
        self.assertIsNone(build(builder.review()).commit_oid())


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
