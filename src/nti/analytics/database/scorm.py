#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics.common import timestamp_type

from nti.analytics.database import get_analytics_db

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_root_context_ids

from nti.analytics.database.resources import get_resource_id

from nti.analytics.database.users import get_or_create_user

from nti.analytics.identifier import get_ntiid_id

from nti.analytics_database.scorm import SCORMResourceViews


def create_launch_record(user, course, metadata, nti_session, context_path, timestamp):
    db = get_analytics_db()
    
    user_record = get_or_create_user(user)
    uid = user_record.user_id
    sid = nti_session
    rid = get_ntiid_id(metadata)
    rid = get_resource_id(db, rid, create=True)
    timestamp = timestamp_type(timestamp)
    context_path = get_context_path(context_path)
    course_id, entity_root_context_id = get_root_context_ids(course)
    
    # TODO: Check if record exists?
    
    new_object = SCORMResourceViews(user_id=uid,
                                    session_id=sid,
                                    timestamp=timestamp,
                                    course_id=course_id,
                                    entity_root_context_id=entity_root_context_id,
                                    context_path=context_path,
                                    resource_id=rid,
                                    time_length=None)
    db.session.add(new_object)
    