from src.asana import helpers as asana_helpers
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build

class TestExtractAttachments(BaseClass):
    def test_extract_no_attachments(self):
        github_comment = build(
            builder.comment()
            .body("No urls here!! ![but some weird formatting] (oops)")
        )
        attachments = asana_helpers.extract_attachments(github_comment)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachment_with_unknown_extension(self):
        github_comment = build(
            builder.comment()
            .body("Ok here it is ![photoo ooo](www.photopng.com/this.fakeg) and there it was")
        )
        attachments = asana_helpers.extract_attachments(github_comment)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachments_with_extensions(self):
        github_comment = build(
            builder.comment()
            .body("Ok here's the first: ![photo.png](www.photopng.com/this.png) and the second!! ![giferino.gif](giphy.com/example.gif)")
        )
        attachments = asana_helpers.extract_attachments(github_comment)
        self.assertListEqual(
            attachments,
            [
                ["photo.png", "www.photopng.com/this.png", "image/png"],
                ["giferino.gif", "giphy.com/example.gif", "image/gif"]
            ]
        )

    def test_extract_attachment_without_extension(self):
        github_comment = build(
            builder.comment()
            .body("Ok here's the first: ![photo](www.photopng.com/this.png) and that's it!")
        )
        attachments = asana_helpers.extract_attachments(github_comment)
        self.assertListEqual(
            attachments,
            [
                ["photo.png", "www.photopng.com/this.png", "image/png"],
            ]
        )

    

if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()