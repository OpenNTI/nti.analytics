#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.analytics_database import Base
from nti.analytics_database import INTID_COLUMN_TYPE
from nti.analytics_database import NTIID_COLUMN_TYPE
from nti.analytics_database import SESSION_COLUMN_TYPE

from nti.analytics_database.interfaces import IAnalyticsDB


def get_analytics_db(strict=True):
    if strict:
        return component.getUtility(IAnalyticsDB)
    else:
        return component.queryUtility(IAnalyticsDB)


def resolve_objects(to_call, rows, **kwargs):
    result = ()
    if rows:
        # Resolve the objects, filtering out Nones
        result = [x for x in (to_call(row, **kwargs) for row in rows)
                  if x is not None]
    return result


def should_update_event(old_record, new_time_length):
    """
    For a record with a 'time_length' field, decide whether the
    event should be updated based on the new time_length given. This
    allows clients to heartbeat update the view event.
    """
    # We want to update if our new time_length is greater than the old,
    # or if our old time_length is none.
    return old_record.time_length is None \
        or old_record.time_length < new_time_length
