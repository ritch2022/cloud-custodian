# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import jmespath

from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod


@resources.register("clb")
class CLB(QueryResourceManager):
    """CLB"""

    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "LoadBalancerId"
        endpoint = "clb.tencentcloudapi.com"
        service = "clb"
        version = "2018-03-17"
        enum_spec = ("DescribeLoadBalancers", "Response.LoadBalancerSet[]", {})
        metrics_instance_id_name = "LoadBalancerId"
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "clb"
        taggable = True

    def augment(self, resources_param):
        instances = jmespath.search("filters[*].Instances", self.data)
        if instances:
            for resource in resources_param:
                cli = self.get_client()
                resp = cli.execute_query("DescribeTargets",
                                         {"LoadBalancerId": resource["LoadBalancerId"]})
                listeners = resp["Response"]["Listeners"]
                instance_ids = []
                for listener in listeners:
                    for rule in listener["Rules"]:
                        for target in rule["Targets"]:
                            instance_ids.append(target["InstanceId"])
                    for target in listener["Targets"]:
                        instance_ids.append(target["InstanceId"])
                resource["Instances"] = instance_ids
        return resources_param
