# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import json
import logging

import pytz
import jmespath
from dateutil.parser import parse
from datetime import datetime, timedelta

from retrying import RetryError
from tencentcloud.common.exception import TencentCloudSDKException

from c7n.filters import FilterValidationError, Filter
from c7n.exceptions import PolicyValidationError, PolicyExecutionError
from c7n.utils import type_schema, chunks
from c7n_tencentcloud.actions.core import TencentCloudBaseAction

DEFAULT_TAG = "maid_status"


def register_tag_actions(actions):
    """register tag actions"""
    actions.register('tag', AddTagAction)
    actions.register('remove-tag', DeleteTagAction)
    actions.register('rename-tag', RenameTagAction)

    actions.register('mark-for-op', TagDelayedAction)


def register_tag_filters(filters):
    """register tag filters"""
    filters.register('marked-for-op', TagActionFilter)


class TagAction(TencentCloudBaseAction):
    """tag base action"""

    def __init__(self, data=None, manager=None, log_dir=None):
        super().__init__(data, manager, log_dir)

        self.endpoint = "tag.tencentcloudapi.com"
        self.service = "tag"
        self.version = "2018-08-13"
        self.region = ""
        self.log = logging.getLogger("custodian.tencentcloud.actions.TagAction")
        self.batch_size = 10
        self.tags = []

    def process(self, resources):
        self.process_tag_op(resources)

    def _get_request_params(self, resources, tags):
        """
        _get_request_params
        The tag request parameter, the default is to add the tag parameter,
        if the action is UnTagResources, it means to delete the tag
        """
        qcs_list = self.manager.source.get_resource_qcs(resources)

        if self.action == "UnTagResources":
            return {"ResourceList": qcs_list, "TagKeys": tags}
        else:
            return {"ResourceList": qcs_list, "Tags": tags}

    def process_tag_op(self, resources):
        """process_tag"""
        try:
            client = self.get_client()
            for batch in chunks(resources, self.batch_size):
                params = self._get_request_params(batch, self.tags)
                resp = client.execute_query(self.action, params)
                failed_resources = jmespath.search("Response.FailedResources[]", resp)
                params_str = json.dumps(params)
                if len(failed_resources) != 0:
                    self.log.error("operation failed. %s , params: %s", self.data.get('type'),
                                   params_str)
                self.log.debug("%s , params: %s ", self.data.get('type'), params_str)
            return True
        except (RetryError, TencentCloudSDKException) as err:
            raise PolicyExecutionError(err) from err


class AddTagAction(TagAction):
    """
    Add tag information
    """
    schema = type_schema("tag",
                         key={"type": "string"},
                         value={"type": "string"})
    schema_alias = True

    def __init__(self, data=None, manager=None, log_dir=None):
        super().__init__(data, manager, log_dir)
        self.action = "TagResources"
        self.tags = [{"TagKey": self.data.get("key"), "TagValue": self.data.get("value")}]

    def validate(self):
        """validate"""
        if not self.data.get('key') or not self.data.get('value'):
            raise PolicyValidationError("Must specify key")
        return self


class RenameTagAction(TagAction):
    """
    Rename the tag information, because Tencent Cloud API does not support direct modification,
    you need to delete it first and then add it
    """
    schema = type_schema("rename-tag",
                         old_key={"type": "string"},
                         new_key={"type": "string"})
    schema_alias = True

    def validate(self):
        """validate"""
        if not self.data.get('old_key') or not self.data.get('new_key'):
            raise PolicyValidationError("Must specify key")
        return self

    def _get_tag_params(self, resources):
        old_key = self.data.get('old_key')
        tags = resources[0]["Tags"]
        for t in tags:
            if t["Key"] == old_key:
                return t
        return None

    def process(self, resources, event=None):
        """
        process
        Add tags first, then delete tags
        """
        old_tag = self._get_tag_params(resources)

        if old_tag is not None:
            self.action = "TagResources"
            self.tags = [{"TagKey": self.data.get("new_key"), "TagValue": old_tag["Value"]}]
            add_ok = self.process_tag_op(resources)
            if add_ok:
                self.action = "UnTagResources"
                self.tags = [self.data.get('old_key')]
                self.process_tag_op(resources)


class DeleteTagAction(TagAction):
    """Delete Tag"""
    schema = type_schema("remove-tag",
                         tag={"type": "string"},
                         tags={"type": "array"},
                         msg={"type": "string"})
    schema_alias = True

    def __init__(self, data=None, manager=None, log_dir=None):
        super().__init__(data, manager, log_dir)
        self.action = "UnTagResources"
        self.tags = self.data.get("tags")

    def validate(self):
        """validate"""
        if not self.data.get('tags'):
            raise FilterValidationError("Must specify tags")
        return self


class TagDelayedAction(TagAction):
    """
    Tag resources for future action.
    """
    schema = type_schema(
        "mark-for-op",
        tag={"type": "string"},
        msg={"type": "string"},
        days={"type": "number", "minimum": 0},
        hours={"type": "number", "minimum": 0},
        # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        # TZ database name
        tz={"type": "string"},
        op={"type": "string"})
    schema_alias = True

    default_template = "Resource does not meet policy: {op}@{action_date}"

    def __init__(self, data=None, manager=None, log_dir=None):
        super().__init__(data, manager, log_dir)
        self.resource_type = self.manager.get_model()
        try:
            self.tz = pytz.timezone(self.data.get("tz", "utc"))
        except pytz.exceptions.UnknownTimeZoneError as err:
            raise PolicyValidationError(f"Invalid tz specified in {self.manager.data}") from err

    def get_permissions(self):
        """get_permissions"""
        return self.manager.action_registry["tag"].permissions

    def validate(self):
        """validate"""
        op = self.data.get("op")
        if self.manager and op not in self.manager.action_registry.keys():
            raise PolicyValidationError(f"mark-for-op invalid op:{op} in {self.manager.data}")
        return self

    def generate_timestamp(self, days, hours):
        """generate_timestamp"""
        n = datetime.now(tz=self.tz).replace(second=0, microsecond=0)
        action_datetime = n + timedelta(days=days, hours=hours)
        return datetime.isoformat(action_datetime)

    def _get_config_values(self):
        """get_config_values"""
        days = self.data.get("days", 0)
        hours = self.data.get("hours", 0)
        if not days and not hours:
            # set days = 4 if both days and hours are not set
            days = 4

        config = {
            "op": self.data.get("op", "stop"),
            "tag": self.data.get("tag", DEFAULT_TAG),
            "msg": self.data.get("msg", self.default_template),
            "tz": self.data.get("tz", "utc"),
            "days": days,
            "hours": hours
        }
        config["action_date"] = self.generate_timestamp(days, hours)
        return config

    def process(self, resources):
        """process"""
        cfg = self._get_config_values()
        msg = cfg["msg"].format(op=cfg["op"], action_date=cfg["action_date"])

        self.log.info("Tagging %d resources for %s on %s",
                      len(resources),
                      cfg["op"],
                      cfg["action_date"])

        self.tags = [{"TagKey": cfg["tag"], "TagValue": msg}]
        self.action = "TagResources"
        self.process_tag_op(resources)


class TagActionFilter(Filter):
    """TagActionFilter"""
    schema = type_schema(
        "marked-for-op",
        tag={"type": "string"},
        # not sure why we need to config the tz
        # mark-for-op tag's value contains the tz info
        # NOTICE: we don't use the tz here
        # tz={"type": "string"},
        skew={"type": "number", "minimum": 0},
        skew_hours={"type": "number", "minimum": 0},
        op={"type": "string"}
    )
    schema_alias = True
    current_date = None
    log = logging.getLogger("custodian.tencentcloud.filters.TagActionFilter")

    def validate(self):
        """validate"""
        op = self.data.get("op")
        if self.manager and op not in self.manager.action_registry.keys():
            raise PolicyValidationError(
                f"Invalid marked-for-op op:{op} in {self.manager.data}")
        return self

    def process(self, resources, event=None):
        """process"""
        self.tag = self.data.get("tag", DEFAULT_TAG)
        self.op = self.data.get("op", "stop")
        self.skew = self.data.get("skew", 0)
        self.skew_hours = self.data.get("skew_hours", 0)
        return super(TagActionFilter, self).process(resources, event)

    def __call__(self, resource):
        tag_value = None
        for it in resource.get("Tags", []):
            if it["Key"] == self.tag:
                tag_value = it["Value"]
                break

        if tag_value is None:
            return False

        if ":" not in tag_value or "@" not in tag_value:
            return False

        _, tgt = tag_value.split(":", 1)
        action, action_date_str = tgt.strip().split("@", 1)

        if action != self.op:
            return False

        try:
            action_dt = parse(action_date_str)
        except Exception:
            self.log.error("could not parse tag:%s value:%s on %s",
                           self.tag, tag_value, resource[self.manager.resource_type.id])
            return False

        # current_date must match timezones with the parsed date string
        # NOTICE: we only use the tz from tag_value
        current_dt = datetime.now(tz=action_dt.tzinfo)
        return current_dt >= (action_dt - timedelta(days=self.skew, hours=self.skew_hours))
