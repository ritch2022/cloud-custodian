# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytest
from tc_common import BaseTest


class TestTCR(BaseTest):

    @pytest.mark.vcr
    def test_tcr(self):
        policy = self.load_policy(
            {
                "name": "tcr-lifecycle-rule",
                "resource": "tencentcloud.tcr",
                "filters": [{"type": "lifecycle-rule", "state": False}]
            }
        )
        resources = policy.run()
        assert len(resources) > 0
