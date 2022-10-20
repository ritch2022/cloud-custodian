# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
from c7n.utils import type_schema, local_session

from c7n.filters import Filter

from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod


@resources.register("vpc")
class VPC(QueryResourceManager):
    """
    vpc - Virtual Private Cloud (VPC)
    https://www.tencentcloud.com/document/product/215/535?lang=en&pg=
    """

    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "VpcId"
        endpoint = "vpc.tencentcloudapi.com"
        service = "vpc"
        version = "2017-03-12"
        enum_spec = ("DescribeVpcs", "Response.VpcSet[]", {})
        metrics_instance_id_name = "natId"
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": "20"}}
        resource_prefix = "vpc"
        taggable = True


@VPC.filter_registry.register('flow-logs')
class FlowLogFilter(Filter):
    """Are flow logs enabled on the resource.

    ie to find all vpcs with flows logs disabled we can do this

    :example:
    .. code-block:: yaml
            policies:
              - name: flow-mis-configured
                resource: vpc
                    filters:
                      - type: flow-logs
                        enabled: false

    """

    schema = type_schema(
        'flow-logs',
        **{'enabled': {'type': 'boolean', 'default': False}})

    def __init__(self, data, manager=None):
        super().__init__(data, manager)
        self.resource_type = self.manager.get_model()

    def process(self, resources, event=None):
        client = local_session(self.manager.session_factory).client(self.resource_type.endpoint,
                                                                    self.resource_type.service,
                                                                    self.resource_type.version,
                                                                    self.manager.config.region)

        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resp = client.execute_paged_query("DescribeFlowLogs", {},
                                          "Response.FlowLog[]",
                                          paging_def)
        vpcIds = [r["VpcId"] for r in resp if r['Enable'] == self.data.get('enabled')]

        return [r for r in resources if r['VpcId'] in vpcIds]
