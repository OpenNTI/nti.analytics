#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import component

from nti.app.products.courseware_ims.interfaces import ILTILaunchEvent

from nti.analytics.database import lti as db_lti

from nti.analytics.database.users import get_user

from nti.analytics.sessions import get_nti_session_id

get_lti_asset_launches_by_user = db_lti.get_launch_records_by_user
get_lti_asset_launches = db_lti.get_launch_records
get_lti_asset_launches_for_ntiid = db_lti.get_launch_records_for_ntiid


def get_active_users_with_lti_asset_launches(**kwargs):
    for user_id, count in get_lti_asset_launches_by_user(**kwargs):
        user = get_user(user_id)
        if user:
            yield user, count


def _add_launch_record(user, course, asset, nti_session, timestamp):
    context_path = [course.ntiid]
    db_lti.create_launch_record(user, course, asset, nti_session, context_path, timestamp)


@component.adapter(ILTILaunchEvent)
def _lti_asset_launched(event):
    nti_session = get_nti_session_id()
    _add_launch_record(event.user, event.course, event.asset, nti_session, event.timestamp)
