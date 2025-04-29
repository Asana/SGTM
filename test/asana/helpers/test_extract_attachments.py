from src.asana import helpers as asana_helpers
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


class TestExtractAttachments(BaseClass):
    def test_extract_no_attachments(self):
        github_html = "No urls here!! <img alt=\"but some weird formatting\" /> (oops)"
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachment_with_unknown_extension(self):
        github_html = (
            "Ok here it is <img src=\"www.photopng.com/this.fakeg\" alt=\"photoo ooo\" /> and there it was"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertEqual(len(attachments), 0)

    def test_extract_attachments_with_extensions(self):
        github_html = (
            "Ok here's the first: <img src=\"www.photopng.com/this.png\" alt=\"photo\" /> and the"
            " second!! <img src=\"giphy.com/example.gif\" alt=\"giferino\" />"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png",
                    file_type="image/png",
                ),
                asana_helpers.AttachmentData(
                    file_name="giferino.gif",
                    file_url="giphy.com/example.gif",
                    file_type="image/gif",
                ),
            ],
        )

    def test_extract_attachments_with_double_extensions(self):
        github_html = (
            "Ok here's the first: <img src=\"www.photopng.com/this.png/this-small.png\" alt=\"photo\" /> and the"
            " second!! <img src=\"giphy.com/cute-cat.jpg/small.jpg\" alt=\"cute-cat\" />"
            " third! <img src=\"giphy.com/even-cuter-cat.jpg/small.jpg\" alt=\"even-cuter-cat\" />"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png/this-small.png",
                    file_type="image/png",
                ),
                asana_helpers.AttachmentData(
                    file_name="cute-cat.jpg",
                    file_url="giphy.com/cute-cat.jpg/small.jpg",
                    file_type="image/jpeg",
                ),
                asana_helpers.AttachmentData(
                    file_name="even-cuter-cat.jpg",
                    file_url="giphy.com/even-cuter-cat.jpg/small.jpg",
                    file_type="image/jpeg",
                ),
            ],
        )
    
    def test_extract_attachment_with_github_asset_url(self):
        github_html = (
            "Ok here's the first: <img src=\"https://api.github.com/assets/long-unique-uuid.png?token=123321\" alt=\"github-asset\" /> and that's it!"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(attachments, [
            asana_helpers.AttachmentData(
                file_name="github-asset.png",
                file_url="https://api.github.com/assets/long-unique-uuid.png?token=123321",
                file_type="image/png",
            ),
        ])
    
    def test_extract_attachment_with_github_img_tag_url(self):
        github_html = (
            "For some reason, github also has img tags like this: <img width=\"745\" alt=\"Screenshot 2025-04-22 at 19 43 43\" src=\"https://api.github.com/assets/long-unique-uuid.png?token=123321\" />"
            "inside markdown comments. This should not be a problem for us."
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(attachments, [
            asana_helpers.AttachmentData(
                file_name="Screenshot 2025-04-22 at 19 43 43.png",
                file_url="https://api.github.com/assets/long-unique-uuid.png?token=123321",
                file_type="image/png",
            ),
        ])
        
    def test_extract_attachment_with_github_video_url(self):
        github_html = (
            "Ok here's the first: <video src=\"https://api.github.com/assets/long-unique-uuid.mov?token=123321\" /> and that's it!"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(attachments, [
            asana_helpers.AttachmentData(
                file_name="long-unique-uuid.mov",
                file_url="https://api.github.com/assets/long-unique-uuid.mov?token=123321",
                file_type="video/mov",
            ),
        ])

    def test_extract_attachment_without_extension(self):
        github_html = (
            "Ok here's the first: <img src=\"www.photopng.com/this.png\" alt=\"photo\" /> and that's it!"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="photo.png",
                    file_url="www.photopng.com/this.png",
                    file_type="image/png",
                ),
            ],
        )

    def test_extract_attachment_no_file_name_given(self):
        github_html = (
            "Ok here's the first: <img src=\"www.photopng.com/this.png\" alt=\"\" /> and that's it!"
        )
        attachments = asana_helpers._extract_attachments(github_html)
        self.assertListEqual(
            attachments,
            [
                asana_helpers.AttachmentData(
                    file_name="this.png",
                    file_url="www.photopng.com/this.png",
                    file_type="image/png",
                ),
            ],
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
