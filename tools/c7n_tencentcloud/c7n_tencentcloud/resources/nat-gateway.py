# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytz
from datetime import datetime
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod


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
        tz = pytz.timezone("Asia/Shanghai")
        for resource in resources:
            dt = tz.localize(datetime.strptime(resource["CreatedTime"], "%Y-%m-%d %H:%M:%S"))
            resource["CreatedTime"] = dt.astimezone(pytz.utc).isoformat()
        return resources
