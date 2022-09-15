# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import pytest
from tc_common import BaseTest
from c7n_tencentcloud.resources.cvm import CVM


class TestCvmTagAction(BaseTest):
    @pytest.fixture(autouse=True)
    def set_ctx(self, ctx):
        self.ctx = ctx
        policy = {
            "name": "cvm-test",
            "query": {
                    "InstanceIds": ["ins-00lycyy6"]
            },
        }
        self.cvm = CVM(self.ctx, policy)

    @pytest.mark.vcr
    def test_cvm_mark_op_stop(self, options):
        resources = self.cvm.resources()
        assert not resources[0]["Tags"]

        policy = self.load_policy(
            {
                "name": "cvm-mark-for-op-stop",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-00lycyy6"]
                },
                "actions": [
                    {
                        "type": "mark-for-op",
                        "op": "stop",
                        "days": 14
                    }
                ]
            },
            config=options
        )
        policy.run()

        resources = self.cvm.resources()
        assert resources[0]["Tags"][0]["Key"] == "maid_status"

    @pytest.mark.vcr
    def test_cvm_marked_op_stop_not_filter(self, options):
        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "RUNNING"

        policy = self.load_policy(
            {
                "name": "cvm-marked-for-op-stop",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-00lycyy6"]
                },
                "filters": [
                    {
                        "type": "marked-for-op",
                        "op": "stop",
                        "skew": 14
                    }, {
                        "not": [{
                            "type": "marked-for-op",
                            "op": "stop",
                            "skew": 14
                        }]
                    }
                ], "actions": [
                    {
                        "type": "stop"
                    }
                ]
            },
            config=options
        )
        policy.run()

        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "RUNNING"

    @pytest.mark.vcr
    def test_cvm_marked_op_stop(self, options):
        resources = self.cvm.resources()
        assert resources[0]["InstanceState"] == "RUNNING"

        policy = self.load_policy(
            {
                "name": "cvm-marked-for-op-stop",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-00lycyy6"]
                },
                "filters": [
                    {
                        "type": "marked-for-op",
                        "op": "stop",
                        "skew": 14
                    }
                ], "actions": [
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
    def test_cvm_mark_op_terminate_and_stop(self, options):
        policy = {
            "query": {
                "InstanceIds": ["ins-7sg50hs2"]
            }
        }
        cvm = CVM(self.ctx, policy)
        resources = cvm.resources()
        assert resources[0]["InstanceState"] == "RUNNING"
        assert not resources[0]["Tags"]

        policy = self.load_policy(
            {
                "name": "cvm-mark-for-op-terminate",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-7sg50hs2"]
                },
                "actions": [
                    {
                        "type": "mark-for-op",
                        "op": "terminate",
                        "days": 7
                    },
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
        assert resources[0]["Tags"][0]["Key"] == "maid_status"

    @pytest.mark.vcr
    def test_cvm_marked_op_terminate(self, options):
        policy = {
            "query": {
                "InstanceIds": ["ins-7sg50hs2"]
            }
        }
        cvm = CVM(self.ctx, policy)
        assert len(cvm.resources()) == 1

        policy = self.load_policy(
            {
                "name": "cvm-marked-for-op-terminate",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-7sg50hs2"]
                },
                "filters": [
                    {
                        "type": "marked-for-op",
                        "op": "terminate",
                        "skew": 7
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
    def test_add_tag(self, options):
        resources = self.cvm.resources()
        for tag in resources[0]["Tags"]:
            assert tag["Key"] != "tag_add_test_key_for_test"

        policy = self.load_policy(
            {
                "name": "cvm-test-tag",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-00lycyy6"]
                },
                "actions": [
                    {
                        "type": "tag",
                        "key": "tag_add_test_key_for_test",
                        "value": "tag_add_test_value_for_test"
                    }
                ]
            },
            config=options
        )
        policy.run()

        resources = self.cvm.resources()
        tag_add_success = False
        for tag in resources[0]["Tags"]:
            if tag["Key"] == "tag_add_test_key_for_test" and \
                    tag["Value"] == "tag_add_test_value_for_test":
                tag_add_success = True
                break
        assert tag_add_success

    @pytest.mark.vcr
    def test_modify_tag(self, options):
        resources = self.cvm.resources()
        tag_exist = False
        for tag in resources[0]["Tags"]:
            if tag["Key"] == "tag_add_test_key_for_test":
                tag_exist = True
                break
        assert tag_exist

        policy = self.load_policy(
            {
                "name": "cvm-test-rename-tag",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-00lycyy6"]
                },
                "actions": [
                    {
                        "type": "rename-tag",
                        "old_key": "tag_add_test_key_for_test",
                        "new_key": "tag_add_test_key_for_test_rename"
                    }
                ]
            },
            config=options
        )
        policy.run()

        old_key_not_exist = True
        new_key_exist = False
        resources = self.cvm.resources()
        for tag in resources[0]["Tags"]:
            if tag["Key"] == "tag_add_test_key_for_test":
                old_key_not_exist = False
                break
            if tag["Key"] == "tag_add_test_key_for_test_rename":
                new_key_exist = True
        assert old_key_not_exist and new_key_exist

    @pytest.mark.vcr
    def test_remove_tag(self, options):
        resources = self.cvm.resources()
        tag_exist = False
        for tag in resources[0]["Tags"]:
            if tag["Key"] == "tag_add_test_key_for_test_rename":
                tag_exist = True
                break
        assert tag_exist

        policy = self.load_policy(
            {
                "name": "cvm-test-remove-tag",
                "resource": "tencentcloud.cvm",
                "query": {
                    "InstanceIds": ["ins-00lycyy6"]
                },
                "actions": [
                    {
                        "type": "remove-tag",
                        "tags": ["tag_add_test_key_for_test_rename"]
                    }
                ]
            },
            config=options
        )
        policy.run()

        resources = self.cvm.resources()
        for tag in resources[0]["Tags"]:
            assert tag["Key"] != "tag_add_test_key_for_test_rename"
