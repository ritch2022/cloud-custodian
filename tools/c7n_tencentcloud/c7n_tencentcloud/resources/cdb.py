# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager
from c7n_tencentcloud.utils import PageMethod, isoformat_datetime_str
import pytz


@resources.register("cdb")
class CDB(QueryResourceManager):
    """cdb"""

    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "InstanceId"
        endpoint = "cdb.tencentcloudapi.com"
        service = "cdb"
        version = "2017-03-20"
        enum_spec = ("DescribeDBInstances", "Response.Items[]", {})
        metrics_instance_id_name = "InstanceId"
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "instanceId"
        taggable = True

        datetime_fields_format = {
            "CreateTime": ("%Y-%m-%d %H:%M:%S", pytz.timezone("Asia/Shanghai"))
        }

    def augment(self, resources):
        for resource in resources:
            cli = self.get_client()
            resp = cli.execute_query("DescribeDBInstanceInfo",
                                     {"InstanceId": resource["InstanceId"]})
            encryption = resp["Response"]["Encryption"]
            resource["Encryption"] = encryption

            field_format = self.resource_type.datetime_fields_format["CreateTime"]
            resource["CreateTime"] = isoformat_datetime_str(resource["CreateTime"],
                                                            field_format[0],
                                                            field_format[1])
        return resources
