from src.asana import helpers as asana_helpers
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


class TestExtractAttachments(BaseClass):
    def test_extract_no_attachments(self):
        github_comment = "No urls here!! ![but some weird formatting] (oops)"
        attachments = asana_helpers._extract_attachments(github_comment)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachment_with_unknown_extension(self):
        github_comment = (
            "Ok here it is ![photoo ooo](www.photopng.com/this.fakeg) and there it was"
        )
        attachments = asana_helpers._extract_attachments(github_comment)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachments_with_extensions(self):
        github_comment = (
            "Ok here's the first: ![photo.png](www.photopng.com/this.png) and the"
            " second!! ![giferino.gif](giphy.com/example.gif)"
        )
        attachments = asana_helpers._extract_attachments(github_comment)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png",
                    image_type="image/png",
                ),
                asana_helpers.AttachmentData(
                    file_name="giferino.gif",
                    file_url="giphy.com/example.gif",
                    image_type="image/gif",
                ),
            ],
        )

    def test_extract_attachment_without_extension(self):
        github_comment = (
            "Ok here's the first: ![photo](www.photopng.com/this.png) and that's it!"
        )
        attachments = asana_helpers._extract_attachments(github_comment)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png",
                    image_type="image/png",
                ),
            ],
        )

    def test_extract_attachment_no_file_name_given(self):
        github_comment = (
            "Ok here's the first: ![](www.photopng.com/this.png) and that's it!"
        )
        attachments = asana_helpers._extract_attachments(github_comment)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="github_attachment.png",
                    file_url="www.photopng.com/this.png",
                    image_type="image/png",
                ),
            ],
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
