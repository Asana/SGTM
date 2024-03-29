from .builder_base_class import BuilderBaseClass
from .comment_builder import CommentBuilder
from .pull_request_builder import PullRequestBuilder
from .review_builder import ReviewBuilder
from .user_builder import UserBuilder
from .commit_builder import CommitBuilder
from .label_builder import LabelBuilder
from .check_suite_builder import CheckSuiteBuilder
from .check_run_builder import CheckRunBuilder


class Builder(object):
    def comment(self, *args, **keywords):
        return CommentBuilder(*args, **keywords)

    def pull_request(self, *args, **keywords):
        return PullRequestBuilder(*args, **keywords)

    def review(self, *args, **keywords):
        return ReviewBuilder(*args, **keywords)

    def user(self, *args, **keywords):
        return UserBuilder(*args, **keywords)

    def commit(self, *args, **keywords):
        return CommitBuilder(*args, **keywords)

    def label(self, *args, **keywords):
        return LabelBuilder(*args, **keywords)

    def check_suite(self, *args, **keywords):
        return CheckSuiteBuilder(*args, **keywords)

    def check_run(self, *args, **keywords):
        return CheckRunBuilder(*args, **keywords)


def build(builder: BuilderBaseClass):
    return builder.build()


builder = Builder()
