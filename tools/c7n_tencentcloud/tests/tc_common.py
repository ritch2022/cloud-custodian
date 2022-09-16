# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
import pytest

from c7n.schema import generate
from c7n.testing import CustodianTestCore


class BaseTest(CustodianTestCore):

    def addCleanup(self, func, *args, **kw):
        pass

    custodian_schema = generate()

    @property
    def account_id(self):
        return ""

    @pytest.fixture(autouse=True)
    def init(self, vcr):
        if vcr:
            self.recording = len(vcr.data) == 0
        else:
            self.recording = True
