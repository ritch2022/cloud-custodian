# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import time

import pytest
from tc_common import BaseTest
from c7n_tencentcloud.resources.cvm import CVM
from c7n_tencentcloud.resources.cvm import CvmStopAction
from c7n.exceptions import PolicyExecutionError


class TestCvmAction(BaseTest):

    @pytest.mark.vcr
    def test_cvm_stop(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-stop-test",
                "resource": "tencentcloud.cvm",
                "comment": "stop cvm",
                "query": [{
                    "InstanceIds": ["ins-00lycyy6"]
                }],
                "filters": [{"InstanceState": "RUNNING"}],
                "actions": [
                    {
                        "type": "stop"
                    }
                ]
            },
            config=options
        )
        resources = policy.run()
        assert resources
        if self.recording:
            time.sleep(10)
        resources = policy.resource_manager.source.resources()
        assert resources[0]["InstanceState"] in ("STOPPING", "STOPPED")

    @pytest.mark.vcr
    def test_cvm_start(self, options, cvm):
        policy = self.load_policy(
            {
                "name": "cvm-start-test",
                "resource": "tencentcloud.cvm",
                "comment": "start cvm",
                "query": [{
                    "InstanceIds": ["ins-00lycyy6"]
                }],
                "actions": [
                    {
                        "type": "start"
                    }
                ]
            },
            config=options
        )
        resources = policy.run()
        assert resources[0]["InstanceState"] == "STOPPED"
        if self.recording:
            time.sleep(10)
        resources = cvm.resources()
        assert resources[0]["InstanceState"] == "STARTING" or \
               resources[0]["InstanceState"] == "RUNNING"

    @pytest.mark.vcr
    def test_cvm_terminate(self, options, ctx):
        policy = self.load_policy(
            {
                "name": "cvm-terminate-test",
                "resource": "tencentcloud.cvm",
                "comment": "terminate cvm",
                "query": [{
                    "InstanceIds": ["ins-8ktxnl0g"]
                }],
                "actions": [
                    {
                        "type": "terminate"
                    }
                ]
            },
            config=options
        )
        resources = policy.run()
        assert len(resources) == 1
        if self.recording:
            time.sleep(10)
        policy = {
            "query": [{
                "InstanceIds": ["ins-8ktxnl0g"]
            }]
        }
        cvm = CVM(ctx, policy)
        assert len(cvm.resources()) == 0

    @pytest.mark.vcr
    def test_cvm_exec_exception(self, monkeypatch, cvm):
        def get_params(*args):
            return {"InstanceIds": "hello"}
        stop = CvmStopAction({'type': 'stop'}, cvm)
        monkeypatch.setattr(stop, "get_request_params", get_params)
        with pytest.raises(PolicyExecutionError):
            stop.process(cvm.resources())
