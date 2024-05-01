# pyright: basic
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sys
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from github import Github
from github.Auth import Auth as GithubAuthABC, TOKEN_REFRESH_THRESHOLD_TIMEDELTA
from github.NamedUser import NamedUser
import requests
from typing_extensions import TypedDict
from typing import (
    Hashable,
    Optional,
    Protocol,
    cast,
)
from typing_extensions import TypeAlias

from src.config import GITHUB_API_KEY


Key: TypeAlias = Hashable


class TokenContainer(Protocol):
    """
    A protocol for a container of a Github token, which can be used to authenticate with the Github
    API.

    Documented as the response schema for
    https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28#create-an-installation-access-token-for-an-app

    According to the schema, only token and expires_at are required, but the other fields are
    present on the InstallationAuthorization objects provided by PyGithub.
    """

    # Not modeled: repositories, single_file, has_multiple_single_files, single_file_paths

    @property
    def token(self) -> str: ...

    @property
    def expires_at(self) -> Optional[datetime]: ...

    @property
    def on_behalf_of(self) -> Optional[NamedUser]: ...

    @property
    def repository_selection(self) -> Optional[str]: ...


# Mimicks the interface provided by InstallationAuthorization.
@dataclass(frozen=True)
class GithubPAT:
    token: str
    expires_at: Optional[datetime] = None

    @property
    def on_behalf_of(self):
        return None

    @property
    def repository_selection(self):
        return None


class TokenDict(TypedDict):
    token: str
    expires_at: Optional[str]


class GithubIndirectClientAuth(GithubAuthABC):
    """
    A GithubAuthABC implementation that uses an AsanaGithubAppTokenAuth to get a token for
    authentication. Makes it possible to use the Github SDK continuously without directly accessing
    the private key.
    """

    def __init__(self, github_auth: "AsanaGithubAppTokenAuth"):
        self._github_auth = github_auth
        self._token: Optional[TokenContainer] = None

    def _refresh(self) -> TokenContainer:
        token = self._github_auth.get_token()
        self._token = token
        return token

    @property
    def token_type(self) -> str:
        return "Bearer"

    @property
    def token(self) -> str:
        return (
            self._refresh().token
            if not self._token or self._is_expired
            else self._token.token
        )

    @property
    def _is_expired(self) -> bool:
        return (
            not self._token
            or self._token.expires_at is not None
            and self._token.expires_at.replace(tzinfo=timezone.utc)
            < datetime.now(timezone.utc) - TOKEN_REFRESH_THRESHOLD_TIMEDELTA
        )

    @property
    def expires_at(self) -> Optional[datetime]:
        return self._token.expires_at if self._token else None


class AsanaGithubAuth(ABC):
    @abstractmethod
    def get_token(self) -> TokenContainer: ...

    # This method is separate and overridable to support use-cases where the client can refresh its
    # token.
    def get_client(self, repo_name: Optional[str] = None) -> Github:
        return Github(self.get_token().token)

    def or_local(self) -> "AsanaGithubAuth":
        if sys.platform.startswith("darwin"):
            return AsanaGithubLocalAuth()
        return self


@dataclass(frozen=True)
class AsanaGithubLocalAuth(AsanaGithubAuth):
    def get_token(self):
        # To avoid adding as a dependency to Lambda bundles:
        return GithubPAT(token=GITHUB_API_KEY)

    # This is not intended to be used from extremely generic contexts, so fail if called.
    def or_local(self) -> "AsanaGithubAuth":
        raise Exception("This is already a local auth")


class AsanaGithubAppTokenAuth(AsanaGithubAuth):
    def __init__(self, github_app_name: str, session: Optional[boto3.Session] = None):
        self.github_app_name = github_app_name
        self.session = session or boto3.Session()

    def get_token(self) -> TokenContainer:
        """
        Get the token needed to authenticate with a GitHub App, without directly accessing the
        private key. This approach is preferred over AsanaGithubAppAuth whenever possible.

        Use this function to retrieve a 1-hour token for a Github App installation.

        For context, see:
        - Asana docs on using GH Apps: https://github.com/Asana/codez/blob/next-master/asana2/docs/github/github_apps.md
        - AWS docs on SigV4 signing requests: https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html#sigv4-authenticated-requests-python
        """

        # The URL and request format are specified in: https://github.com/Asana/codez/blob/next-master/asana2/docs/github/github_apps.md
        get_token_endpoint = (
            "https://jv2fqfrofl7veyzrfiizx4i7hq0joruw.lambda-url.us-east-1.on.aws/"
        )
        data = json.dumps(dict(github_app_name=self.github_app_name))

        # Sign the request with SigV4Auth.
        creds = self.session.get_credentials()
        assert creds, "No credentials available to sign the request."
        aws_request = AWSRequest(
            method="POST",
            url=get_token_endpoint,
            data=data,
            params=None,
            headers={"content-type": "application/json"},
        )
        sigV4Auth = SigV4Auth(
            creds.get_frozen_credentials(),
            service_name="lambda",
            region_name="us-east-1",
        )
        sigV4Auth.add_auth(aws_request)

        response = requests.request(
            method="POST",
            url=get_token_endpoint,
            headers=dict(aws_request.headers),
            data=data,
            timeout=30,
        )

        if not response.ok:
            raise ValueError(
                f"Failed to get GitHub App token: {response.content.decode()}"
            )

        token = cast(TokenDict, response.json())
        return GithubPAT(
            token=token["token"],
            expires_at=(
                datetime.strptime(token["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
                if token["expires_at"]
                else None
            ),
        )

    def get_client(self, repo_name: Optional[str] = None) -> Github:
        return Github(auth=GithubIndirectClientAuth(self))


sgtm_github_auth = AsanaGithubAppTokenAuth(github_app_name="asana-sgtm")
