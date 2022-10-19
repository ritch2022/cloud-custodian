# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytest
from tc_common import BaseTest


class TestCdb(BaseTest):

    @pytest.mark.vcr
    def test_cdb_backup_create_time(self):
        policy = self.load_policy(
            {
                "name": "test_cdb_backup_create_time",
                "resource": "tencentcloud.cdb-backup",
                "filters": [
                    {
                        "type": "value",
                        "key": "Date",
                        "value": 1,
                        "value_type": "age",
                        "op": "greater-than"
                    }
                ]
            }
        )
        resources = policy.run()
        assert len(resources) > 0
