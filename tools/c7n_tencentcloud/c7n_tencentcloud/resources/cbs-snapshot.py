# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytz
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod, isoformat_date_str


@resources.register("cbs-snapshot")
class CBSSnapshot(QueryResourceManager):
    """cbs-snapshot"""

    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "SnapshotId"
        endpoint = "cbs.tencentcloudapi.com"
        service = "cvm"
        version = "2017-03-12"
        enum_spec = ("DescribeSnapshots", "Response.SnapshotSet[]", {})
        metrics_instance_id_name = "SnapshotId"
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "volume"
        taggable = True

    def augment(self, resources):
        for resource in resources:
            isoformat_date_str(resource, ["CreateTime"], "%Y-%m-%d %H:%M:%S",)
        return resources
