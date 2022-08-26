# SPDX-License-Identifier: Apache-2.0

import os
from tencentcloud.common.credential import Credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.common_client import CommonClient


ENV_AK = "TENCENTCLOUD_SECRET_ID"
ENV_SK = "TENCENTCLOUD_SECRET_KEY"


def get_aksk():
    """
    It returns a tuple of two strings, the first one is the AK, the second one is the SK
    :return: A tuple of strings.
    """
    return (os.environ[ENV_AK], os.environ[ENV_SK])


class Client:
    """Client"""
    def __init__(self,
                credential: Credential,
                service: str,
                version: str,
                profile: ClientProfile,
                region: str) -> None:
        self._cli = CommonClient(service, version, credential, region, profile)

    def execute_query(self, action: str, params: dict) -> dict:
        """execute_query"""
        return self._cli.call_json(action, params)


class Session:
    """Session"""
    def __init__(self) -> None:
        self._secret_id, self._secret_key = get_aksk()
        self._cred = Credential(self._secret_id, self._secret_key)

    def client(self,
               endpoint: str,
               service: str,
               version: str,
               region: str) -> Client:
        """client"""
        http_profile = HttpProfile()
        http_profile.endpoint = endpoint

        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        cli = Client(self._cred, service, version, client_profile, region)
        return cli
