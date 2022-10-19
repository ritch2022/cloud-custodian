# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager, DescribeSource
from c7n_tencentcloud.utils import PageMethod


class LogGroupDescribe(DescribeSource):
    def augment(self, resources):
        """
        Resource comes with tags, no need to re-query
        """
        return resources


@resources.register("cls")
class LogTopic(QueryResourceManager):
    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "TopicId"
        endpoint = "cls.tencentcloudapi.com"
        service = "cls"
        version = "2020-10-16"
        enum_spec = ("DescribeTopics", "Response.Topics[]", {})
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "topic"
        taggable = True

    source_mapping = {'describe': LogGroupDescribe}
