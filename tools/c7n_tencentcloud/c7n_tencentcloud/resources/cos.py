# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
from concurrent.futures import as_completed

import jmespath
from qcloud_cos import CosS3Client, CosConfig, CosServiceError

from c7n.filters import Filter, ValueFilter
from c7n_tencentcloud.provider import resources
from c7n_tencentcloud.query import QueryResourceManager, ResourceTypeInfo, DescribeSource
from c7n.utils import type_schema, format_string_values
from tencentcloud.common import credential

log = logging.getLogger('custodian.cos')


class DescribeCos(DescribeSource):

    @staticmethod
    def get_cos_client(region):
        cred = credential.DefaultCredentialProvider().get_credentials()
        config = CosConfig(Region=region, SecretId=cred.secret_id,
                           SecretKey=cred.secret_key)
        return CosS3Client(config)

    def resources(self, params=None):
        resp = self.get_cos_client(self.resource_manager.config.region).list_buckets()
        action, jsonpath, extra_params = self.resource_type.enum_spec
        resources = jmespath.search(jsonpath, resp)
        resources = [r for r in resources if r["Location"] == self.resource_manager.config.region]

        self.augment(resources)
        return resources

    def get_resource_qcs(self, resources):
        """
        get_resource_qcs
        resource description https://cloud.tencent.com/document/product/598/10606
        """
        qcs_list = []
        for r in resources:
            # get appid
            names = r[self.resource_type.id].split('-')
            appid = names[len(names) - 1]

            qcs = "qcs::{}:{}:uid/{}:{}".format(
                self.resource_type.service,
                self.region,
                appid,
                r[self.resource_type.id])
            qcs_list.append(qcs)
        return qcs_list


@resources.register("cos")
class COS(QueryResourceManager):
    class resource_type(ResourceTypeInfo):
        id = "Name"
        service = 'cos'
        resource_prefix = "prefix"
        enum_spec = ('list_buckets', 'Buckets.Bucket[]', None)

    source_mapping = {'describe': DescribeCos}


class BucketFilterBase(Filter):
    def get_std_format_args(self, bucket):
        return {
            'account_id': self.manager.config.account_id,
            'region': self.manager.config.region,
            'bucket_name': bucket['Name'],
            'bucket_region': bucket['Location']
        }


@COS.filter_registry.register('has-statement')
class HasStatementFilter(BucketFilterBase):
    schema = type_schema(
        'has-statement',
        statements={
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'Sid': {'type': 'string'},
                    'Effect': {'type': 'string', 'enum': ['Allow', 'Deny']},
                    'Principal': {'anyOf': [
                        {'type': 'string'},
                        {'type': 'object'}, {'type': 'array'}]},
                    'Action': {
                        'anyOf': [{'type': 'string'}, {'type': 'array'}]},
                    'Resource': {
                        'anyOf': [{'type': 'string'}, {'type': 'array'}]},
                },
                'required': ['Effect']
            }
        })

    def process(self, resources, event=None):
        return list(filter(None, map(self.process_resource, resources)))

    def get_policy(self, b):
        try:
            return self.manager.source.get_cos_client(b["Location"]).get_bucket_policy(
                Bucket=b['Name'])
        except CosServiceError as e:
            # For the cos interface, if the data cannot be queried,
            # the cos client returns an error code whose code is NoSuch prefix.
            if not e.get_error_code().startswith("NoSuch"):
                self.log.error('error cos client error:%s\n%s', b['Name'], e.get_error_msg())
            return None

    def process_resource(self, resource):
        p = self.get_policy(resource)
        if p is None:
            return None

        statements = json.loads(p["Policy"]).get('Statement', [])

        required_statements = format_string_values(list(self.data.get('statements', [])),
                                                   **self.get_std_format_args(resource))
        for required_statement in required_statements:
            for statement in statements:
                found = 0
                for key, value in required_statement.items():
                    if key in ['Action', 'Resource']:
                        if key in statement and value in statement[key]:
                            found += 1
                    elif key == "Principal":
                        if key in statement and value in statement[key]["qcs"]:
                            found += 1
                    else:
                        if key in statement and value == statement[key]:
                            found += 1
                if found and found == len(required_statement):
                    required_statements.remove(required_statement)
                    break

        if self.data.get('statements', []) and not required_statements:
            return resource
        return None


@COS.filter_registry.register('bucket-encryption')
class BucketEncryption(Filter):
    """Filters for cos buckets that have bucket-encryption
    :example

    policies:
    - name: cos
      resource: tencentcloud.cos
      filters:
        - type: bucket-encryption
          state: False
    """
    schema = type_schema('bucket-encryption',
                         state={'type': 'boolean'},
                         crypto={'type': 'string', 'enum': ['AES256']})

    def process(self, buckets, event=None):
        results = []
        with self.executor_factory(max_workers=2) as w:
            futures = {w.submit(self.process_bucket, b): b for b in buckets}
            for future in as_completed(futures):
                b = futures[future]
                if future.exception():
                    self.log.error("Message: %s Bucket: %s", future.exception(),
                                   b['Name'])
                    continue
                if future.result():
                    results.append(b)
        return results

    def process_bucket(self, b):
        rules = []
        try:
            resp = self.manager.source.get_cos_client(b["Location"]).get_bucket_encryption(
                Bucket=b['Name'])
            rules = resp["Rule"]
        except CosServiceError as e:
            if not e.get_error_code().startswith("NoSuch"):
                self.log.error('error cos client error:%s\n%s', b['Name'], e.get_error_msg())

        if self.data.get('state', True):
            for sse in rules:
                return self.filter_bucket(sse)
            return False
        else:
            # If there is no configuration information,rules==[]
            return rules is []

    def filter_bucket(self, sse):
        # only support ASE256 now
        crypto = self.data.get('crypto')
        if not crypto:
            return True

        rule = sse['ApplyServerSideEncryptionByDefault']
        return crypto == rule['SSEAlgorithm']


@COS.filter_registry.register('bucket-logging')
class BucketLoggingFilter(BucketFilterBase):
    """
    Filter based on bucket logging configuration
    """
    schema = type_schema(
        'bucket-logging',
        op={'enum': ['enabled', 'disabled', 'equal', 'not-equal', 'eq', 'ne']},
        required=['op'],
        target_bucket={'type': 'string'},
        target_prefix={'type': 'string'})
    schema_alias = False

    def get_logging(self, b):
        try:
            return self.manager.source.get_cos_client(b["Location"]).get_bucket_logging(
                Bucket=b['Name'])
        except CosServiceError as e:
            if not e.get_error_code().startswith("NoSuch"):
                self.log.error('error cos client error:%s\n%s', b['Name'], e.get_error_msg())
            return {}

    def process(self, buckets, event=None):
        return list(filter(None, map(self.process_bucket, buckets)))

    def process_bucket(self, b):
        if self.match_bucket(b):
            return b

    def match_bucket(self, b):
        op = self.data.get('op')
        config_logging = self.get_logging(b)

        if op == 'disabled':
            return config_logging == {}
        elif op == 'enabled':
            return config_logging != {}
        config_logging = config_logging.get("LoggingEnabled")

        variables = self.get_std_format_args(b)
        variables.update({
            'account': self.manager.config.account_id,
            'source_bucket_name': b['Name'],
            'source_bucket_region': b['Location'],
            'target_bucket_name': self.data.get('target_bucket'),
            'target_prefix': self.data.get('target_prefix'),
        })
        data = format_string_values(self.data, **variables)
        target_bucket = data.get('target_bucket')
        target_prefix = data.get('target_prefix', b['Name'] + '/')

        target_config = {
            "TargetBucket": target_bucket,
            "TargetPrefix": target_prefix
        } if target_bucket else {}

        if op in ('not-equal', 'ne'):
            return config_logging != target_config
        else:
            return config_logging == target_config


@COS.filter_registry.register('bucket-lifecycle')
class BucketLifecycle(Filter):
    """
    Filter based on bucket lifecycle configuration
    """
    schema = type_schema('bucket-lifecycle',
                         key={'type': 'string'},
                         value={'type': 'string'},
                         value_type={'type': 'string'},
                         op={'type': 'string'}, )

    def get_lifecycle(self, b):
        try:
            return self.manager.source.get_cos_client(b["Location"]).get_bucket_lifecycle(
                Bucket=b['Name'])
        except CosServiceError as e:
            if not e.get_error_code().startswith("NoSuch"):
                self.log.error('error cos client error:%s\n%s', b['Name'], e.get_error_msg())
        return None

    def process(self, buckets, event=None):
        return list(filter(None, map(self.process_bucket, buckets)))

    def process_bucket(self, b):
        lifecycles = self.get_lifecycle(b)
        if lifecycles is None:
            return None

        matcher_config = dict(self.data)
        real_key = self.data["key"].split(".")[-1]
        matcher_config["key"] = real_key

        v_filter = ValueFilter(matcher_config)
        v_filter.annotate = False

        results = jmespath.search(self.data["key"], lifecycles)

        matched = []
        for item in results:
            data = {
                real_key: item
            }
            if v_filter.match(data):
                matched.append(data)

        if bool(matched):
            return b