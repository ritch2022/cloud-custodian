# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytest
from tc_common import BaseTest


class TestVpc(BaseTest):

    @pytest.mark.vcr
    def test_vpc_flowlogs_enabled_pull(self):
        policy = self.load_policy(
            {
                "name": "vpc-flowlogs-enabled-pull",
                "resource": "tencentcloud.vpc",
                "filters": [
                    {
                        "type": "flow-logs",
                        "enabled": False
                    }
                ]
            }
        )
        resources = policy.run()
        assert not resources
