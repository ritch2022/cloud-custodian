# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytz
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod, isoformat_date_str


@resources.register("nat-gateway")
class NatGateway(QueryResourceManager):
    """nat-gateway"""

    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "NatGatewayId"
        endpoint = "vpc.tencentcloudapi.com"
        service = "vpc"
        version = "2017-03-12"
        enum_spec = ("DescribeNatGateways", "Response.NatGatewaySet[]", {})
        metrics_instance_id_name = "NatGatewayId"
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "nat"
        taggable = True

    def augment(self, resources):
        from_tz = pytz.timezone("Asia/Shanghai")
        for resource in resources:
            isoformat_date_str(resource,
                               ["CreatedTime"],
                               "%Y-%m-%d %H:%M:%S",
                               from_tz,
                               pytz.utc)
        return resources
