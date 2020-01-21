#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics_database.profile_views import EntityProfileViews
from nti.analytics_database.profile_views import EntityProfileActivityViews
from nti.analytics_database.profile_views import EntityProfileMembershipViews

from nti.analytics.common import get_entity
from nti.analytics.common import timestamp_type

from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database._utils import get_context_path

from nti.analytics.database.users import get_or_create_user

logger = __import__('logging').getLogger(__name__)


def _profile_view_exists(db, table, user_id, target_id, timestamp):
	return db.session.query(table).filter(
							table.user_id == user_id,
							table.target_id == target_id,
							table.timestamp == timestamp).first()


def _create_profile_view(event, table, nti_session):
	db = get_analytics_db()
	user = get_entity(event.user)
	user = get_or_create_user(user)

	target = get_entity(event.ProfileEntity)
	target = get_or_create_user(target)

	timestamp = timestamp_type(event.timestamp)
	context_path = get_context_path(event.context_path)

	existing_record = _profile_view_exists(db, table, user.user_id,
										   target.user_id, timestamp)
	time_length = event.time_length
	sid = nti_session

	if existing_record is not None:
		if should_update_event(existing_record, time_length):
			existing_record.time_length = time_length
		return

	view_record = table(session_id=sid,
						timestamp=timestamp,
						context_path=context_path,
						time_length=time_length)
	view_record._user_record = user
	view_record._target_record = target
	db.session.add(view_record)
	logger.debug('Profile view event (user=%s) (target=%s)',
				 event.user, event.ProfileEntity)


def create_profile_view(event, nti_session):
	_create_profile_view(event, EntityProfileViews, nti_session)


def create_profile_activity_view(event, nti_session):
	_create_profile_view(event, EntityProfileActivityViews, nti_session)


def create_profile_membership_view(event, nti_session):
	_create_profile_view(event, EntityProfileMembershipViews, nti_session)
