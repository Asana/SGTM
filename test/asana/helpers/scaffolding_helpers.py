from test.impl.builders import CommentBuilder, ReviewBuilder, PullRequestBuilder


def create_github_user(login, name = None):
    return login, name


def create_comment(**keywords):
    builder = CommentBuilder()
    return _populate_subobjects(builder, builder.raw_comment, keywords).build()


def create_review(**keywords):
    builder = ReviewBuilder()
    return _populate_subobjects(builder, builder.raw_review, keywords).build()


def create_pull_request(**keywords):
    builder = PullRequestBuilder()
    return _populate_subobjects(builder, builder.raw_pr, keywords).build()


def _snake_case_to_lower_camel_case(snake_cased_string: str) -> str:
    """
    Converts a string that is known to be in snake_case to a lowerCamelCase string
    """
    snake_segments = snake_cased_string.split('_')
    snake_head, snake_tail = snake_segments[0], snake_segments[1:]
    lowered_camel_head = snake_head.lower()
    camel_humps = [snake_segment.title() for snake_segment in snake_tail]
    return lowered_camel_head + "".join(camel_humps)


def _populate_subobjects(builder, raw_content, keywords):
    for k, v in keywords.items():
        if not k.startswith(""):
            raw_content[_snake_case_to_lower_camel_case(k)] = v
    if "author" in keywords:
        login, name = keywords["author"]
        builder = builder.author(login, name)
    else:
        builder = builder.author("github_author_login", "GITHUB_AUTHOR_NAME")
    sub_objects = ["body", "reviews", "comments", "assignees", "requested_reviewers"]
    for sub_object in sub_objects:
        if sub_object in keywords:
            setter = getattr(builder, sub_object)
            builder = setter(keywords[sub_object])
    return builder
