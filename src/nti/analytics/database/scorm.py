#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics.common import timestamp_type

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_root_context_ids

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.resources import get_resource_id
from nti.analytics.database.resources import get_resource_record

from nti.analytics.database.users import get_or_create_user

from nti.analytics.identifier import get_ntiid_id

from nti.analytics_database.scorm import SCORMPackageLaunches


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
    
    new_object = SCORMPackageLaunches(user_id=uid,
                                      session_id=sid,
                                      timestamp=timestamp,
                                      course_id=course_id,
                                      entity_root_context_id=entity_root_context_id,
                                      context_path=context_path,
                                      resource_id=rid,
                                      time_length=None)
    db.session.add(new_object)
    
    
def _resolve_launch_record(record, root_context=None, user=None):
    if root_context is not None:
        record.RootContext = root_context
    if user is not None:
        record.user = user
    return record


def get_launch_records(user=None, root_context=None, **kwargs):
    launch_records = get_filtered_records(user, SCORMPackageLaunches, root_context=root_context, **kwargs)
    return resolve_objects(_resolve_launch_record, launch_records,
                           user=user, root_context=root_context)
    
    
def get_launch_records_for_ntiid(metadata_ntiid, user=None, root_context=None, **kwargs):
    results = ()
    db = get_analytics_db()
    resource_record = get_resource_record(db, metadata_ntiid)
    if resource_record is not None:
        resource_id = resource_record.resource_id
        filters = (SCORMPackageLaunches.resource_id == resource_id)
        launch_records = get_filtered_records(user,
                                              SCORMPackageLaunches,
                                              root_context=root_context,
                                              filters=filters,
                                              **kwargs)
        results = resolve_objects(_resolve_launch_record, launch_records,
                                  user=user, root_context=root_context)
    return results
    