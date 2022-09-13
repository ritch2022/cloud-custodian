# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
from c7n.schema import generate
from c7n.testing import CustodianTestCore

class BaseTest(CustodianTestCore):
    custodian_schema = generate()

    @property
    def account_id(self):
        return ""
