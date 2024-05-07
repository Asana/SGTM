# pyright: basic
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
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

from src.config import (
    GITHUB_API_KEY,
    GITHUB_APP_NAME,
    GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL,
    GITHUB_APP_NAME,
)


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


@dataclass(frozen=True)
class GithubToken:
    """
    A simple implementation of a TokenContainer that only contains a token and an optional
    expiration. this class can be instantiated.
    """

    token: str
    expires_at: Optional[datetime] = None

    @property
    def on_behalf_of(self):
        return None

    @property
    def repository_selection(self):
        return None


class GithubAutoRefreshedAppTokenAuth(GithubAuthABC):
    """
    A pygithub.Auth.GithubAuthABC implementation that uses an AsanaGithubAppTokenAuth to get a token
    for authentication. A pygithub.Github object can be instantiated directly with an instance of
    this class, and pygithub will automatically handle auto-refreshing the token based on the
    `expires_at` property.

    This class caches tokens, and returns the cached token unless it's expired. If it's expired, it
    returns a refreshed token when `.token()` is called.
    """

    def __init__(self, github_auth: "SGTMGithubAppTokenAuth"):
        self._github_auth = github_auth
        self._token: Optional[TokenContainer] = None

    def _refresh(self) -> TokenContainer:
        token = self._github_auth.get_token()
        self._token = token
        return token

    @property
    def token_container(self) -> TokenContainer:
        """
        Get the token container. This method caches the token, and returns the cached token unless
        it's expired. If it's expired, it returns a refreshed token.
        """
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
        """
        Get the expiration time of the token.
        """
        return self._token.expires_at if self._token else None


class SGTMGithubAuth(Protocol):
    """
    A protocol for a class that provides authentication for interacting with the Github API. This
    protocol is used to abstract the authentication mechanism away from the rest of the codebase. It
    is used to provide a consistent way to get a Github client and a GraphQL endpoint, irrespective
    of whether the authentication is done using a personal access token or a Github App token.
    """

    def get_token(self) -> TokenContainer:
        ...

    def get_rest_client(self) -> Github:
        ...

    def get_graphql_endpoint(self) -> HTTPEndpoint:
        ...


@dataclass(frozen=True)
class SGTMGithubLocalAuth(SGTMGithubAuth):
    """
    A simple implementation of SGTMGithubAuth that uses a personal access token to authenticate with
    the Github API. This class can be instantiated.
    """

    @override
    def get_token(self):
        return GithubToken(token=GITHUB_API_KEY)

    @override
    def get_rest_client(self) -> Github:
        return Github(self.get_token().token)

    @override
    def get_graphql_endpoint(self) -> HTTPEndpoint:
        headers = {"Authorization": f"bearer {self.get_token().token}"}
        return HTTPEndpoint("https://api.github.com/graphql", headers)


class GithubAutoRefreshedGraphQLEndpoint(HTTPEndpoint):
    """
    A wrapper around a GraphQL endpoint. This wrapper sets the authentication headers using Github
    App based authentication (as implemented in GithubAutoRefreshedTokenAuth), and automatically
    refreshes the Github App installation access token when it expires.
    """

    __current_token: Optional[TokenContainer] = None
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


class SGTMGithubAppTokenAuth(SGTMGithubAuth):
    """
    A class that provides authentication for interacting with the Github API using a Github App
    token. This class can be instantiated.

    The Github App token is retrieved from an endpoint whose URL is defined in the
    GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL environment variable. This class uses the
    boto3 library to sign the request to the token retrieval endpoint with SigV4Auth.
    """

    def __init__(self, github_app_name: str, session: Optional[boto3.Session] = None):
        self.github_app_name = github_app_name
        self.session = session or boto3.Session()
        self.__auto_refreshed_auth_obj = GithubAutoRefreshedAppTokenAuth(self)

    class TokenDict(TypedDict):
        """
        A dictionary representing the response from the token retrieval URL endpoint.
        """

        token: str
        expires_at: Optional[str]

    class EndpointRequestBody(TypedDict):
        """
        A dictionary representing the request body for the token retrieval URL endpoint.
        """

        github_app_name: str

    @override
    def get_token(self) -> TokenContainer:
        """
        Get the token needed to authenticate with a GitHub App by retrieving a 1-hour token from the
        endpoint whose url is defined in GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL.

        Invariants:
        - This endpoint should accept a SIGV4-signed POST request with a JSON body that specifies a value
        for the 'github_app_name' key.
        - The post request should return a JSON object with a 'token' key that contains the Github
        token, and an 'expires_at' key which contains a timestamp of the format
        '%Y-%m-%dT%H:%M:%SZ'.

        For context, see:
        - AWS docs on SigV4 signing requests: https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html#sigv4-authenticated-requests-python
        """

        data = json.dumps(
            SGTMGithubAppTokenAuth.EndpointRequestBody(
                github_app_name=self.github_app_name
            )
        )

        assert GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL, (
            "GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL is not set. "
            "Please set this environment variable."
        )

        # Sign the request with SigV4Auth.
        creds = self.session.get_credentials()
        assert creds, "No credentials available to sign the request."
        aws_request = AWSRequest(
            method="POST",
            url=GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL,
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
            url=GITHUB_APP_INSTALLATION_ACCESS_TOKEN_RETRIEVAL_URL,
            headers=dict(aws_request.headers),
            data=data,
            timeout=30,
        )

        if not response.ok:
            raise ValueError(
                f"Failed to get GitHub App token: {response.content.decode()}"
            )

        token = cast(SGTMGithubAppTokenAuth.TokenDict, response.json())
        return GithubToken(
            token=token["token"],
            expires_at=(
                datetime.strptime(token["expires_at"], "%Y-%m-%dT%H:%M:%SZ")
                if token["expires_at"]
                else None
            ),
        )

    @override
    def get_rest_client(self) -> Github:
        return Github(auth=self.__auto_refreshed_auth_obj)

    @override
    def get_graphql_endpoint(self) -> HTTPEndpoint:
        return GithubAutoRefreshedGraphQLEndpoint(self.__auto_refreshed_auth_obj)


if sys.platform.startswith("darwin") or os.getenv("CIRCLECI") == "true":
    # If we're running on a local mac or in CircleCI, use the local auth (where we expect
    # that `GITHUB_API_KEY` env var is set)
    sgtm_github_auth: SGTMGithubAuth = SGTMGithubLocalAuth()
else:
    # Otherwise, use Github App based auth
    assert (
        GITHUB_APP_NAME
    ), "GITHUB_APP_NAME is not set. Please set this environment variable."
    sgtm_github_auth: SGTMGithubAuth = SGTMGithubAppTokenAuth(
        github_app_name=GITHUB_APP_NAME
    )
