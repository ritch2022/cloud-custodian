# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import time

import pytest
from tc_common import BaseTest


class TestClb(BaseTest):

    @pytest.mark.vcr
    def test_clb_filter_value(self):
        policy = self.load_policy(
            {
                "name": "test_clb",
                "resource": "tencentcloud.clb",
                "description": "filter load balancers has not been requested for the long time",
                "query": [{
                    "LoadBalancerIds": ["lb-n6g4mc26"]
                }],
                "filters": [
                    {
                        "type": "value",
                        "key": "CreateTime",
                        "value_type": "age",
                        "value": 30,
                        "op": "gte"
                    }
                ]
            }
        )
        resources = policy.run()
        time_array = time.strptime(resources[0]["CreateTime"], "%Y-%m-%d %H:%M:%S")
        assert time.time() > time.mktime(time_array) + 3600 * 24 * 30

    @pytest.mark.vcr
    def test_clb_no_instances_attached(self):
        policy = self.load_policy(
            {
                "name": "test_clb",
                "resource": "tencentcloud.clb",
                "query": [{
                    "LoadBalancerIds": ["lb-aqsfvh8m"]
                }],
                "filters": [
                    {"Instances": []}
                ]
            }
        )
        resources = policy.run()
        assert len(resources) == 1 and len(resources[0]["Instances"]) == 0
