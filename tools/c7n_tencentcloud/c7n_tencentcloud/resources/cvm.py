# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import jmespath
from retrying import RetryError
from tencentcloud.common.exception import TencentCloudSDKException

from c7n.exceptions import PolicyExecutionError
from c7n.utils import type_schema, chunks
from c7n_tencentcloud.actions import TencentCloudBaseAction
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import ResourceTypeInfo, QueryResourceManager, DescribeSource
from c7n_tencentcloud.utils import PageMethod


class CVMDescribe(DescribeSource):
    """CVMDescribe"""
    def augment(self, resources):
        return resources


@resources.register("cvm")
class CVM(QueryResourceManager):
    """CVM"""
    source_mapping = {"describe": CVMDescribe}
    
    class resource_type(ResourceTypeInfo):
        """resource_type"""
        id = "InstanceId"
        endpoint = "cvm.tencentcloudapi.com"
        service = "cvm"
        version = "2017-03-12"
        enum_spec = ("DescribeInstances", "Response.InstanceSet[]", {})
        metrics_instance_id_name = "InstanceId"
        paging_def = {"method": PageMethod.Offset, "limit": {"key": "Limit", "value": 20}}
        resource_prefix = "instance"
        taggable = True
        batch_size = 10


class CvmAction(TencentCloudBaseAction):
    schema_alias = True

    """cvm base api_method_name """

    def process(self, resources):
        for batch in chunks(resources, self.resource_type.batch_size):
            params = self.get_request_params(batch)
            if params is not None:
                self.do_request(params)

    def do_request(self, params):
        """process_cvm"""
        try:
            client = self.get_client()
            resp = client.execute_query(self.t_api_method_name, params)
            failed_resources = jmespath.search("Response.Error", resp)
            if failed_resources is not None:
                raise PolicyExecutionError(f"{self.data.get('type')} error")
            self.log.debug("%s resources: %s, cvm: %s",
                           self.data.get('type'),
                           params['InstanceIds'],
                           params)
        except (RetryError, TencentCloudSDKException) as err:
            raise PolicyExecutionError(err) from err

    def get_request_params(self, resources):
        """
        The default value returns InstanceIds , if there is customization,
        it will be implemented in subclasses
        """
        ids = []
        for resource in resources:
            ids.append(resource[self.resource_type.id])
        if len(ids) > 0:
            return {"InstanceIds": ids}
        return None


@CVM.action_registry.register('stop')
class CvmStopAction(CvmAction):
    """stop_cvm"""
    schema = type_schema("stop")
    t_api_method_name = "StopInstances"

    def get_request_params(self, resources):
        """get_params_stop"""
        ids = []
        for resource in resources:
            if resource["InstanceState"] == "RUNNING":
                ids.append(resource[self.resource_type.id])
        if len(ids) > 0:
            return {
                "InstanceIds": ids,
                "StopType": "SOFT",
                "StoppedMode": "STOP_CHARGING"
            }
        return None


@CVM.action_registry.register('start')
class CvmStartAction(CvmAction):
    """start_cvm"""
    schema = type_schema("start")
    t_api_method_name = "StartInstances"


@CVM.action_registry.register('terminate')
class CvmTerminateAction(CvmAction):
    """terminate_cvm"""
    schema = type_schema("terminate")
    t_api_method_name = "TerminateInstances"
