from uuid import uuid4
from random import randint
from typing import List, Union, Tuple
from datetime import datetime
from src.utils import create_date_string
from src.github.models import PullRequest, Comment, Review


class CommentBuilder(object):
    def __init__(self, body=""):
        self.raw_comment = {
            "id": uuid4().hex,
            "body": body,
            "author": {"login": "", "name": ""},
        }

    def with_body(self, body: str):
        self.raw_comment["body"] = body
        return self

    def with_author(self, login="", name=""):
        self.raw_comment["author"]["login"] = login
        self.raw_comment["author"]["name"] = name
        return self

    def with_created_at(self, created_at: Union[str, datetime]):
        if isinstance(created_at, datetime):
            created_at = create_date_string(created_at)
        self.raw_comment["created_at"] = created_at
        return self

    def build(self) -> Comment:
        return Comment(self.raw_comment)


class ReviewBuilder(object):
    def __init__(self, body=""):
        self.raw_review = {
            "id": uuid4().hex,
            "body": body,
            "author": {"login": "", "name": ""},
            "comments": {"nodes": []},
        }

    def with_state(self, state: str):
        # TODO: validate state
        self.raw_review["state"] = state
        return self

    def with_body(self, body: str):
        self.raw_review["body"] = body
        return self

    def with_author(self, login, name):
        self.raw_review["author"]["login"] = login
        self.raw_review["author"]["name"] = name
        return self

    def with_submitted_at(self, submitted_at: Union[str, datetime]):
        if isinstance(submitted_at, datetime):
            submitted_at = create_date_string(submitted_at)
        self.raw_review["submitted_at"] = submitted_at
        return self

    def with_comments(self, comments: Union[List[CommentBuilder], List[Comment]]):
        for comment in comments:
            if isinstance(comment, Comment):
                self.raw_review["comments"]["nodes"].append(comment.raw_comment)
            else:
                self.raw_review["comments"]["nodes"].append(comment.build().raw_comment)
        return self

    def build(self) -> Review:
        return Review(self.raw_review)


class PullRequestBuilder(object):
    def __init__(self, body=""):
        pr_number = randint(1, 9999999999)
        self.raw_pr = {
            "id": uuid4().hex,
            "number": pr_number,
            "body": body,
            "title": uuid4().hex,
            "url": "https://www.github.com/foo/pulls/" + str(pr_number),
            "assignees": {"nodes": []},
            "comments": {"nodes": []},
            "reviews": {"nodes": []},
            "reviewRequests": {"nodes": []},
            "closed": False,
            "merged": False,
            "author": {"login": "", "name": ""},
            "repository": {
                "id": uuid4().hex,
                "name": uuid4().hex,
                "owner": {"login": uuid4().hex, "name": uuid4().hex,},
            },
        }

    def with_body(self, body: str):
        self.raw_pr["body"] = body
        return self

    def with_merged_at(self, merged_at: Union[str, datetime]):
        if isinstance(merged_at, datetime):
            merged_at = create_date_string(merged_at)
        self.raw_pr["merged_at"] = merged_at
        return self

    def with_comments(self, comments: Union[List[CommentBuilder], List[Comment]]):
        for comment in comments:
            if isinstance(comment, Comment):
                self.raw_pr["comments"]["nodes"].append(comment.raw_comment)
            else:
                self.raw_pr["comments"]["nodes"].append(comment.build().raw_comment)
        return self

    def with_reviews(self, reviews: Union[List[ReviewBuilder], List[Review]]):
        for review in reviews:
            if isinstance(review, Review):
                self.raw_pr["reviews"]["nodes"].append(review.raw_review)
            else:
                self.raw_pr["reviews"]["nodes"].append(review.build().raw_review)
        return self

    def with_author(self, login: str, name: str):
        self.raw_pr["author"]["login"] = login
        self.raw_pr["author"]["name"] = name
        return self

    def with_assignees(self, assignees: List[Tuple[str, str]]):
        for login, name in assignees:
            self.raw_pr["assignees"]["nodes"].append({
                "login": login,
                "name": name
            })
        return self

    def with_requested_reviewers(self, reviewers: List[Tuple[str, str]]):
        for login, name in reviewers:
            self.raw_pr["reviewRequests"]["nodes"].append({"requestedReviewer": {
                "login": login,
                "name": name
            }})
        return self

    def build(self):
        return PullRequest(self.raw_pr)
