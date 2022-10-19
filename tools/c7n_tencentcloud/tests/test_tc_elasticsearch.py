# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytest
from tc_common import BaseTest


class TestElasticsearch(BaseTest):

    @pytest.mark.vcr
    def test_elasticsearch_key(self):
        policy = self.load_policy(
            {
                "name": "elasticsearch-instance-generation",
                "resource": "tencentcloud.elasticsearch",
                "filters": [
                    {
                        "type": "value",
                        "key": "NodeInfoList.NodeType",
                        "op": "in",
                        "value": ["ES.S1.MEDIUM4", "ES.SA2.MEDIUM4"]
                    }
                ]
            }
        )
        resources = policy.run()
        assert not resources
