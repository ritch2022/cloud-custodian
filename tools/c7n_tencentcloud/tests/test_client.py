# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
import jmespath
import numpy
import pytest
import socket
from retrying import RetryError
from c7n_tencentcloud.utils import PageMethod
from c7n.exceptions import PolicyExecutionError
from c7n_tencentcloud.client import Client
from tencentcloud.common.abstract_client import AbstractClient
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException


# data format: (endpoint, service, version, region)
client_test_cases = [
    ("region.tencentcloudapi.com", "region", "2022-06-27", "ap-shanghai"),
    ("region.tencentcloudapi.com", "region", "2022-06-27", "ap-singapore"),
]


@pytest.fixture(params=client_test_cases)
def client(session, request):
    endpoint = request.param[0]
    service = request.param[1]
    version = request.param[2]
    region = request.param[3]
    return session.client(endpoint, service, version, region)


# data format: (method, jsonpath, extra_params)
method_test_cases = [
    ("DescribeProducts", "Response.Products[]", {}),
    ("DescribeZones", "Response.ZoneSet[]", {"Product": "cbs"})
]


@pytest.fixture(params=method_test_cases)
def call_params(request):
    return request.param


def test_call_client(client, call_params):
    action = call_params[0]
    jsonpath = call_params[1]
    param = call_params[2]
    resp = client.execute_query(action, param)
    data = jmespath.search(jsonpath, resp)
    assert data


@pytest.fixture
def client_once(session):
    # just for init, ignore the value
    return session.client("test", "test", "test", "test")


@pytest.fixture
def gen_error_reponse():
    def _make_response(err_code):
        return {
            "Response": {
                "Error": {
                    "Code": err_code
                }
            }
        }
    return _make_response


def test_client_retry_result(client_once, gen_error_reponse, monkeypatch):
    call_counter = 0

    def mock_call_json(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        if call_counter == 3:
            return gen_error_reponse("Invalid")
        return gen_error_reponse("RequestLimitExceeded")

    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)
    client_once.execute_query("test", {})
    assert call_counter == 3


def test_client_retry_exception(client_once, monkeypatch):
    call_counter = 0

    def mock_call_json(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        if call_counter == 3:
            raise TencentCloudSDKException()
        raise socket.error()
    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)
    with pytest.raises(TencentCloudSDKException):
        client_once.execute_query("test", {})

    assert call_counter == 3


def test_client_non_retry_exception(client_once, monkeypatch):
    call_counter = 0

    def mock_call_json(*args, **kwargs):
        nonlocal call_counter
        call_counter += 1
        raise TencentCloudSDKException()

    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)
    with pytest.raises(TencentCloudSDKException):
        client_once.execute_query("test", {})

    assert call_counter == 1


def test_client_over_retry_times(client_once, gen_error_reponse, monkeypatch):
    call_counter = 0
    call_timer = None
    call_at = [0]

    def mock_call_json(*args, **kwargs):
        nonlocal call_counter
        nonlocal call_timer
        nonlocal call_at
        if call_counter == 0:
            call_timer = datetime.now().timestamp()
        else:
            call_at.append(datetime.now().timestamp() - call_timer)
        call_counter += 1
        return gen_error_reponse("RequestLimitExceeded")

    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)
    with pytest.raises(RetryError):
        client_once.execute_query("test", {})
    time_interval = list(numpy.diff(call_at))
    expected_time_interval = [0.2, 0.4, 0.8, 1]
    assert call_counter == 5
    assert all(numpy.isclose(time_interval, expected_time_interval, atol=0.02))


@pytest.fixture
def gen_response():
    def _gen_response(data_id):
        if data_id is not None:
            return {
                "Response": {
                    "InstanceSet": [data_id],
                    "PaginationToken": f"token_{data_id}"
                }
            }
        else:
            return {
                "Response": {
                    "InstanceSet": [],
                    "PaginationToken": ""
                }
            }
    return _gen_response


def test_client_paged_query_offset(client_once, gen_response, monkeypatch):
    start = 0
    total_number = 10
    counter = 0

    def mock_call_json(cls, action, params, *args, **kwargs):
        nonlocal counter
        if counter != params["Offset"]:
            raise Exception(f"wrong offset {params['Offset']} should be {counter}")
        if counter < total_number:
            data = gen_response(start + counter)
            counter += 1
            return data
        else:
            return gen_response(None)
    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)

    data_jsonpath = "Response.InstanceSet[]"
    paging_def = {
        "method": PageMethod.Offset
    }
    params = {
        "Offset": 0
    }
    res = client_once.execute_paged_query("action", params, data_jsonpath, paging_def)
    assert res == list(range(start, start + total_number))


def test_client_paged_query_token(client_once, gen_response, monkeypatch):
    start = 0
    total_number = 10
    counter = 0

    def mock_call_json(cls, action, params, *args, **kwargs):
        nonlocal counter
        if (counter != 0 and params["PaginationToken"] != f"token_{start + counter - 1}"):
            err_msg = f"token got: {params['PaginationToken']} want: token_{start + counter - 1}"
            raise Exception(err_msg)
        if counter < total_number:
            data = gen_response(start + counter)
            counter += 1
            return data
        else:
            return gen_response(None)
    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)

    data_jsonpath = "Response.InstanceSet[]"
    paging_def = {
        "method": PageMethod.PaginationToken,
        "pagination_token_path": "Response.PaginationToken"
    }
    res = client_once.execute_paged_query("action", {}, data_jsonpath, paging_def)
    assert res == list(range(start, start + total_number))


test_cases = [
    {
        "method": ""
    },
    {
        "method": PageMethod.PaginationToken
    },
    {
        "method": PageMethod.PaginationToken,
        "pagination_token_path": ""
    }
]


@pytest.fixture(params=test_cases)
def paging_def(request):
    return request.param


def test_client_paged_query_error(client_once, paging_def):
    data_jsonpath = "Response.InstanceSet[]"
    with pytest.raises(PolicyExecutionError):
        _ = client_once.execute_paged_query("action", {}, data_jsonpath, paging_def)


def test_client_paged_query_over_limit(client_once, monkeypatch):
    assert_value = 1
    monkeypatch.setattr(Client, "MAX_REQUEST_TIMES", assert_value)
    counter = 0

    def mock_call_json(*args, **kwargs):
        nonlocal counter
        counter += 1
        return {
            "Response": {
                "InstanceSet": [1]
            }
        }
    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)

    data_jsonpath = "Response.InstanceSet[]"
    paging_def = {
        "method": PageMethod.Offset
    }
    params = {
        "Offset": 0
    }

    with pytest.raises(PolicyExecutionError):
        _ = client_once.execute_paged_query("action", params, data_jsonpath, paging_def)

    assert counter == assert_value


def test_client_paged_query_over_data_limit(client_once, monkeypatch):
    assert_value = 100
    monkeypatch.setattr(Client, "MAX_RESPONSE_DATA_COUNT", assert_value)
    counter = 0

    def mock_call_json(*args, **kwargs):
        nonlocal counter
        counter += 1
        return {
            "Response": {
                "InstanceSet": [1]
            }
        }
    monkeypatch.setattr(AbstractClient, "call_json", mock_call_json)

    data_jsonpath = "Response.InstanceSet[]"
    paging_def = {
        "method": PageMethod.Offset
    }
    params = {
        "Offset": 0
    }

    with pytest.raises(PolicyExecutionError):
        _ = client_once.execute_paged_query("action", params, data_jsonpath, paging_def)

    assert counter == assert_value
