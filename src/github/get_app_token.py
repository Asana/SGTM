# pyright: basic
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from parser import isexpr
import sys
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from github import Github
from github.Auth import TOKEN_REFRESH_THRESHOLD_TIMEDELTA, Auth as GithubAuthABC
from github.NamedUser import NamedUser
import requests
from typing_extensions import TypedDict, override
from typing import (
    Hashable,
    Optional,
    Protocol,
    cast,
)
from typing_extensions import TypeAlias
from sgqlc.endpoint.http import HTTPEndpoint  # type: ignore

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
    def token(self) -> str:
        ...

    @property
    def expires_at(self) -> Optional[datetime]:
        ...

    @property
    def on_behalf_of(self) -> Optional[NamedUser]:
        ...

    @property
    def repository_selection(self) -> Optional[str]:
        ...


def is_expired(token: TokenContainer) -> bool:
    """
    Check if a token is expired.
    """
    return (
        token.expires_at is not None
        and token.expires_at.replace(tzinfo=timezone.utc)
        < datetime.now(timezone.utc) - TOKEN_REFRESH_THRESHOLD_TIMEDELTA
    )


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


class GithubAutoRefreshedAppTokenAuth(GithubAuthABC):
    """
    A pygithub.Auth.GithubAuthABC implementation that uses an AsanaGithubAppTokenAuth to get a token
    for authentication. Makes it possible to use the Github SDK continuously without directly
    accessing the private key.

    This class caches tokens, and returns the cached token unless it's expired. If it's expired, it
    returns a refreshed token when `.token()` is called.
    """

    def __init__(self, github_auth: "AsanaGithubAppTokenAuth"):
        self._github_auth = github_auth
        self._token: Optional[TokenContainer] = None

    def _refresh(self) -> TokenContainer:
        token = self._github_auth.get_token()
        self._token = token
        return token

    @property
    def token_container(self) -> TokenContainer:
        return (
            # Refresh the token if it's expired or not set.
            # otherwise, return the cached token.
            self._refresh()
            if not self._token or self._is_expired
            else self._token
        )

    @property
    @override
    def token_type(self) -> str:
        return "Bearer"

    @property
    @override
    def token(self) -> str:
        return self.token_container.token

    @property
    def _is_expired(self) -> bool:
        return self._token is None or is_expired(self._token)

    @property
    def expires_at(self) -> Optional[datetime]:
        return self._token.expires_at if self._token else None


class AsanaGithubAuth(ABC):
    @abstractmethod
    def get_token(self) -> TokenContainer:
        ...

    @abstractmethod
    def get_rest_client(self, repo_name: Optional[str] = None) -> Github:
        ...

    @abstractmethod
    def get_graphql_endpoint(self) -> HTTPEndpoint:
        ...

    def or_local(self) -> "AsanaGithubAuth":
        if sys.platform.startswith("darwin") or os.getenv("CIRCLECI") == "true":
            # If we're running on a local mac or in CircleCI, use the local auth (where we expect
            # that `GITHUB_API_KEY` env var is set)
            return AsanaGithubLocalAuth()
        return self


@dataclass(frozen=True)
class AsanaGithubLocalAuth(AsanaGithubAuth):
    @override
    def get_token(self):
        return GithubPAT(token=GITHUB_API_KEY)

    @override
    def get_rest_client(self, repo_name: Optional[str] = None) -> Github:
        return Github(self.get_token().token)

    @override
    def get_graphql_endpoint(self) -> HTTPEndpoint:
        headers = {"Authorization": f"bearer {self.get_token().token}"}
        return HTTPEndpoint("https://api.github.com/graphql", headers)

    @override
    # This is not intended to be used from extremely generic contexts, so fail if called.
    def or_local(self) -> "AsanaGithubAuth":
        raise Exception("This is already a local auth")


class GithubAutoRefreshedGraphQLEndpoint(HTTPEndpoint):
    """
    A wrapper around a GraphQL endpoint. This wrapper sets the authentication headers using Github
    App based authentication (as implemented in GithubAutoRefreshedTokenAuth), and automatically
    refreshes the Github App installation access token when it expires.
    """

    __current_token: TokenContainer
    __auth_refresher: GithubAutoRefreshedAppTokenAuth

    def __init__(self, auth_refresher: GithubAutoRefreshedAppTokenAuth) -> None:
        self.__auth_refresher = auth_refresher
        auth_header = self.__get_new_auth_headers()
        super().__init__("https://api.github.com/graphql", auth_header)

    @override
    def __call__(self, *args, **kwargs) -> dict:
        """
        Execute a GraphQL query against the GitHub API.

        Args:
            query: The GraphQL query to execute.
            variables: The variables to pass to the query.

        Returns:
            The response from the GitHub API.
        """
        if self._needs_refresh():
            self.__update_auth_headers()
        return super().__call__(*args, **kwargs)

    def _needs_refresh(self) -> bool:
        """
        Check if the token needs to be refreshed.
        """
        return self.__current_token is None or is_expired(self.__current_token)

    def __get_new_auth_headers(self) -> dict[str, str]:
        """
        Retrieves a new token and returns an updated Authorization header with the new token.
        """
        self._current_token = self.__auth_refresher.token_container
        return {"Authorization": f"bearer {self._current_token.token}"}

    def __update_auth_headers(self) -> None:
        """
        Refresh the authentication headers.
        """
        self.base_headers.update(self.__get_new_auth_headers())


class AsanaGithubAppTokenAuth(AsanaGithubAuth):
    def __init__(self, github_app_name: str, session: Optional[boto3.Session] = None):
        self.github_app_name = github_app_name
        self.session = session or boto3.Session()
        self.__auto_refreshed_auth_obj = GithubAutoRefreshedAppTokenAuth(self)

    @override
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

    @override
    def get_rest_client(self, repo_name: Optional[str] = None) -> Github:
        return Github(auth=self.__auto_refreshed_auth_obj)

    @override
    def get_graphql_endpoint(self) -> HTTPEndpoint:
        return GithubAutoRefreshedGraphQLEndpoint(self.__auto_refreshed_auth_obj)


sgtm_github_auth = AsanaGithubAppTokenAuth(github_app_name="asana-sgtm").or_local()
