# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import pytest
from tc_common import BaseTest
from c7n_tencentcloud.resources.cvm import CVM
from c7n_tencentcloud.resources.cvm import CvmStopAction
from c7n.exceptions import PolicyExecutionError


# @pytest.fixture(scope="session")
# def get_ctx(ctx):
#     return ctx


# @pytest.fixture
# def config():
#     return Config.empty(**{
#                         "region": "ap-singapore",  # just for init, ignore the value
#                         "output_dir": "null://",
#                         "log_group": "null://",
#                         "cache": False,
#                         })


class TestCvmAction(BaseTest):

    @pytest.fixture(autouse=True)
    def set_ctx(self, ctx):
        self.ctx = ctx
        policy = {
            "name": "cvm-test",
            "filters": [
                {
                    "InstanceId": "ins-00lycyy6"
                }
            ]
        }
        self.cvm = CVM(self.ctx, policy)

    # @pytest.fixture(autouse=True)
    # def set_monkeypatch(self, monkeypatch):
    #     self.monkeypatch = monkeypatch

    @pytest.mark.vcr
    def test_cvm_stop(self, options):
        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "RUNNING"

        policy = self.load_policy(
            {
                "name": "cvm-stop-test",
                "resource": "tencentcloud.cvm",
                "comment": "stop cvm",
                "filters": [
                    {
                        "InstanceId": "ins-00lycyy6"
                    }
                ],
                "actions": [
                    {
                        "type": "stop"
                    }
                ]
            },
            config=options
        )
        policy.run()

        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "STOPPING" or \
               resources[0]["InstanceState"] == "STOPPED"

    @pytest.mark.vcr
    def test_cvm_start(self, options):
        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "STOPPED"

        policy = self.load_policy(
            {
                "name": "cvm-start-test",
                "resource": "tencentcloud.cvm",
                "comment": "start cvm",
                "filters": [
                    {
                        "InstanceId": "ins-00lycyy6"
                    }
                ],
                "actions": [
                    {
                        "type": "start"
                    }
                ]
            },
            config=options
        )
        policy.run()

        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "STARTING" or \
               resources[0]["InstanceState"] == "RUNNING"

    @pytest.mark.vcr
    def test_cvm_terminate(self, options):
        policy = {
            "filters": [
                {
                    "InstanceId": "ins-bqbsb58o"
                }
            ]
        }
        cvm = CVM(self.ctx, policy)
        assert len(cvm.resources()) == 1

        policy = self.load_policy(
            {
                "name": "cvm-terminate-test",
                "resource": "tencentcloud.cvm",
                "comment": "terminate cvm",
                "filters": [
                    {
                        "InstanceId": "ins-bqbsb58o"
                    }
                ],
                "actions": [
                    {
                        "type": "terminate"
                    }
                ]
            },
            config=options
        )
        policy.run()

        assert len(cvm.resources()) == 0

    @pytest.mark.vcr
    def test_cvm_exec_exception(self, monkeypatch):
        def get_params(*args):
            return {"InstanceIds": "hello"}
        stop = CvmStopAction({'type': 'stop'}, self.cvm)
        monkeypatch.setattr(stop, "get_request_params", get_params)
        with pytest.raises(PolicyExecutionError):
            stop.process(self.cvm.resources())
