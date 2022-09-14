# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0

import pytz
from c7n.exceptions import PolicyValidationError

from c7n.actions import BaseAction


class TencentCloudBaseAction(BaseAction):
    def __init__(self, data=None, manager=None, log_dir=None):
        super().__init__(data, manager, log_dir)
        self.resource_type = self.manager.get_model()

        self.endpoint = self.resource_type.endpoint
        self.service = self.resource_type.service
        self.version = self.resource_type.version
        self.region = self.manager.config.region
        self.action = ""

        try:
            self.tz = pytz.timezone(self.data.get("tz", "utc"))
        except pytz.exceptions.UnknownTimeZoneError as err:
            raise PolicyValidationError(f"Invalid tz specified in {self.manager.data}") from err

    def get_client(self):
        return self.manager.session_factory.client(self.endpoint,
                                                   self.service,
                                                   self.version,
                                                   self.region)

    def process(self, resources):
        pass

    def get_request_params(self, resources):
        pass

    def get_permissions(self):
        pass
