# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import jmespath

from c7n.filters import Filter
from c7n.utils import type_schema
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod


@resources.register("tcr")
class TCR(QueryResourceManager):
    """
    TCR - Tencent Container Registry (TCR) is a container image cloud hosting service
    https://www.tencentcloud.com/document/product/614/11254?lang=en&pg=
    """
    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "RegistryId"
        endpoint = "tcr.tencentcloudapi.com"
        service = "tcr"
        version = "2019-09-24"
        enum_spec = ("DescribeInstances", "Response.Registries[]", {})
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "instance"
        metrics_instance_id_name = "tke_cluster_instance_id"
        taggable = True


@TCR.filter_registry.register('lifecycle-rule')
class ImageUnusedFilter(Filter):
    """Lifecycle rule filtering

    :Example:

       policies:
        - name: ecr-life
          resource: tencentcloud.tcr
          filters:
            - type: lifecycle-rule
              state: False
    """
    schema = type_schema(
        'lifecycle-rule',
        state={'type': 'boolean'})

    def process(self, resources, event=None):
        client = self.manager.get_client()

        results = []
        for r in resources:
            resp = client.execute_query("DescribeTagRetentionRules",
                                        {"RegistryId": r[self.manager.resource_type.id]})
            resp_list = jmespath.search("Response.RetentionPolicyList[]", resp)
            if self.data.get('state') == bool(resp_list):
                results.append(r)
        return results
