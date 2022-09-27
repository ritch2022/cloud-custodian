# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import time
import pytest
from tc_common import BaseTest


instance_ids = ["ins-g5ce39ac", "ins-2s6wefc8"]


class TestCvmTagAction(BaseTest):
    @pytest.mark.vcr
    def test_add_tag(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-test-tag",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 2
        for resource in resources:
            for tag in resource["Tags"]:
                assert tag["Key"] != "tag_add_test_key_for_test"
        if self.recording:
            time.sleep(10)

        resources = policy.resource_manager.resources()
        for resource in resources:
            tag_add_success = False
            for tag in resource["Tags"]:
                if tag["Key"] == "tag_add_test_key_for_test" and \
                        tag["Value"] == "tag_add_test_value_for_test":
                    tag_add_success = True
                    break
            assert tag_add_success

    @pytest.mark.vcr
    def test_modify_tag(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-test-rename-tag",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 2
        for resource in resources:
            tag_exist = False
            for tag in resource["Tags"]:
                if tag["Key"] == "tag_add_test_key_for_test":
                    tag_exist = True
                    break
            assert tag_exist
        if self.recording:
            time.sleep(10)

        resources = policy.resource_manager.resources()
        for resource in resources:
            old_key_not_exist = True
            new_key_exist = False
            for tag in resource["Tags"]:
                if tag["Key"] == "tag_add_test_key_for_test":
                    old_key_not_exist = False
                    break
                if tag["Key"] == "tag_add_test_key_for_test_rename":
                    new_key_exist = True
            assert old_key_not_exist and new_key_exist

    @pytest.mark.vcr
    def test_remove_tag(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-test-remove-tag",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
                "actions": [
                    {
                        "type": "remove-tag",
                        "tags": ["tag_add_test_key_for_test_rename"]
                    }
                ]
            },
            config=options
        )
        resources = policy.run()
        assert len(resources) == 2
        for resource in resources:
            tag_exist = False
            for tag in resource["Tags"]:
                if tag["Key"] == "tag_add_test_key_for_test_rename":
                    tag_exist = True
                    break
            assert tag_exist
        if self.recording:
            time.sleep(10)
        resources = policy.resource_manager.resources()
        assert len(resources) == 2
        for resource in resources:
            tag_exist = False
            for tag in resource["Tags"]:
                if tag["Key"] == "tag_add_test_key_for_test_rename":
                    tag_exist = True
                    break
            assert tag_exist is not True

    @pytest.mark.vcr
    def test_cvm_mark_op_stop(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-mark-for-op-stop",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 2
        if self.recording:
            time.sleep(10)
        resources = policy.resource_manager.resources()
        assert all([it["Tags"][0]["Key"] == "maid_status" for it in resources])

    @pytest.mark.vcr
    def test_cvm_marked_op_stop_not_filter(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-marked-for-op-stop",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 0
        if self.recording:
            time.sleep(10)
        resources = policy.resource_manager.resources()
        assert all([it["InstanceState"] == "RUNNING"] for it in resources)

    @pytest.mark.vcr
    def test_cvm_marked_op_stop(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-marked-for-op-stop",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 2
        if self.recording:
            time.sleep(10)
        resources = policy.resource_manager.resources()
        assert all([it["InstanceState"] in ("STOPPING", "STOPPED") for it in resources])
        assert all([it["Tags"][0]["Key"] == "maid_status" for it in resources])

    @pytest.mark.vcr
    def test_cvm_mark_op_terminate_and_stop(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-mark-for-op-terminate",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 2
        if self.recording:
            time.sleep(10)
        resources = policy.resource_manager.resources()
        assert all([it["InstanceState"] in ("STOPPING", "STOPPED") for it in resources])
        assert all([it["Tags"][0]["Key"] == "maid_status" for it in resources])

    @pytest.mark.vcr
    def test_cvm_marked_op_terminate(self, options):
        policy = self.load_policy(
            {
                "name": "cvm-marked-for-op-terminate",
                "resource": "tencentcloud.cvm",
                "query": [{
                    "InstanceIds": instance_ids
                }],
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
        resources = policy.run()
        assert len(resources) == 2
        if self.recording:
            time.sleep(10)

        resources = policy.resource_manager.source.resources()
        current_instance_ids = {it["InstanceId"] for it in resources}
        assert len(current_instance_ids.intersection(set(instance_ids))) == 0
