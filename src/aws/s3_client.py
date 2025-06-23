import boto3  # type: ignore
import json
from contextlib import closing
from typing import Optional, List

from src.config import GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH, AWS_REGION
from src.utils import memoize
from src.logger import logger


class ConfigurationError(Exception):
    pass


class S3Client(object):
    """
    Encapsulates S3 client interface, as exposed to the world. There is a single (singleton) instance of
    S3Client in the process, which is lazily created upon the first request.
    """

    # the singleton instance of S3Client
    _singleton = None

    def __init__(self):
        self.s3_client = S3Client._create_s3_client()
        if (
            "/" in GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH
            and len(GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH) > 3
        ):
            (
                self.github_user_mapping_bucket_name,
                self.github_user_mapping_key_name,
            ) = GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH.split("/", 1)
        else:
            raise ConfigurationError(
                "Configuration error: GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH is not set to a valid S3 path"
            )

    # getter for the singleton
    @classmethod
    def singleton(cls):
        """
        Getter for the S3Client singleton
        """
        if cls._singleton is None:
            cls._singleton = S3Client()
        return cls._singleton

    @staticmethod
    def _create_s3_client():
        return boto3.client("s3", region_name=AWS_REGION)

    @memoize
    def get_asana_domain_user_id_from_github_username(
        self, github_username: str
    ) -> Optional[str]:
        """
        Retrieves the Asana domain user-id associated with a specific GitHub user login, or None,
        if no such association exists.
        """
        if (
            not self.github_user_mapping_bucket_name
            or not self.github_user_mapping_key_name
        ):
            raise ConfigurationError(
                "Configuration error: GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH is not set"
            )
        with closing(
            self.s3_client.get_object(
                Bucket=self.github_user_mapping_bucket_name,
                Key=self.github_user_mapping_key_name,
            )["Body"]
        ) as stream:
            github_identities_to_asana_gids = json.load(stream)

        if github_username in github_identities_to_asana_gids:
            logger.info(
                "Successfully retrieved Asana domain user id from S3 for %s",
                github_username,
            )
            return github_identities_to_asana_gids[github_username]
        else:
            return None


def get_asana_domain_user_id_from_github_handle(github_handle: str) -> Optional[str]:
    """
    Using the singleton instance of S3Client, creating it if necessary:

    Retrieves the Asana domain user-id associated with a specific GitHub user login, or None,
    if no such association exists. User-id associations are created manually via an external
    process.

    If the S3 pathway fails, we fall back to the DynamoDb pathway.
    """

    return S3Client.singleton().get_asana_domain_user_id_from_github_username(
        github_handle
    )
