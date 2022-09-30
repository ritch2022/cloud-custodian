# Copyright The Cloud Custodian Authors.
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime
from enum import Enum


DEFAULT_TAG = "maid_status"


class PageMethod(Enum):
    """
    Paging type enumeration, Enum.Name pagination parameters
    """
    Offset = 0
    PaginationToken = 1


def isoformat_date_str(data: dict,
                      field_keys: list,
                      original_date_str_format: str,
                      timezone_from,
                      timezone_to):
    """
    standardize the date string, using isoformat including timezone info
    example: '2022-09-28T15:28:28+00:00'
    """
    for key in field_keys:
        dt = timezone_from.localize(datetime.strptime(data[key], original_date_str_format))
        data[key] = dt.astimezone(timezone_to).isoformat()
