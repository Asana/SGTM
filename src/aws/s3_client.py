import boto3  # type: ignore
import json
import time
from contextlib import closing
from typing import Any, Optional, List, Set

from src.config import (
    GITHUB_USERNAMES_TO_ASANA_GIDS_S3_PATH,
    AWS_REGION,
    SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_S3_PATH,
)
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


def parse_codeowner_tasks_opt_in_document(document: Any) -> Set[str]:
    """Extract GitHub logins (lower-cased; logins are case-insensitive) from
    the opt-in list document.

    Accepted shapes: a JSON list of logins, or an object
    ``{"version": 1, "opted_in": {"<login>": {...}}}`` where the per-login
    value carries details the opt-in tool records (such as when they opted in).
    """
    if isinstance(document, list):
        return {str(login).lower() for login in document}
    if isinstance(document, dict):
        opted_in = document.get("opted_in")
        if isinstance(opted_in, dict):
            return {str(login).lower() for login in opted_in.keys()}
        if isinstance(opted_in, list):
            return {str(login).lower() for login in opted_in}
    logger.warning("Codeowner tasks opt-in document has an unexpected shape")
    return set()


class CodeownerTasksOptInList(object):
    """
    The list of GitHub logins who opted in to the codeowner-tasks heads-up comment,
    read from S3 and cached briefly so opting in takes effect without a redeploy.
    """

    CACHE_TTL_SECONDS = 60

    _singleton = None

    def __init__(self, s3_path: Optional[str]):
        self.bucket_name: Optional[str] = None
        self.key_name: Optional[str] = None
        if s3_path and "/" in s3_path and not s3_path.startswith("s3://"):
            self.bucket_name, self.key_name = s3_path.split("/", 1)
        elif s3_path:
            logger.error(
                "SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_S3_PATH must be 'bucket/key', "
                f"got {s3_path!r}; treating the opt-in list as empty"
            )
        self.s3_client = boto3.client("s3", region_name=AWS_REGION)
        self._cached_logins: Optional[Set[str]] = None
        self._cached_at = 0.0

    @classmethod
    def singleton(cls) -> "CodeownerTasksOptInList":
        if cls._singleton is None:
            cls._singleton = CodeownerTasksOptInList(
                SGTM_FEATURE__CODEOWNER_TASKS_OPT_IN_S3_PATH
            )
        return cls._singleton

    def logins(self) -> Set[str]:
        """Logins currently opted in. Empty when no list is configured or it
        cannot be read; a stale cached copy is preferred over failing."""
        if not self.bucket_name or not self.key_name:
            return set()
        now = time.monotonic()
        if (
            self._cached_logins is not None
            and now - self._cached_at < self.CACHE_TTL_SECONDS
        ):
            return self._cached_logins
        try:
            with closing(
                self.s3_client.get_object(Bucket=self.bucket_name, Key=self.key_name)[
                    "Body"
                ]
            ) as stream:
                document = json.load(stream)
        except Exception as e:
            logger.warning(
                f"Could not read codeowner tasks opt-in list from "
                f"s3://{self.bucket_name}/{self.key_name}: {e}"
            )
            # Back off for a TTL rather than retrying on every webhook.
            self._cached_at = now
            self._cached_logins = self._cached_logins or set()
            return self._cached_logins
        self._cached_logins = parse_codeowner_tasks_opt_in_document(document)
        self._cached_at = now
        return self._cached_logins


def is_opted_in_to_codeowner_tasks(github_handle: str) -> bool:
    """Whether the author should receive SGTM's codeowner heads-up comment."""
    return github_handle.lower() in CodeownerTasksOptInList.singleton().logins()
