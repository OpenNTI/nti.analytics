#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from datetime import timedelta

from sqlalchemy import and_
from sqlalchemy import or_

from nti.analytics_database.sessions import Sessions
from nti.analytics_database.sessions import UserAgents

from sqlalchemy.orm.session import make_transient

from nti.analytics.common import timestamp_type

from nti.analytics.database import get_analytics_db

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.locations import check_ip_location
from nti.analytics.database.users import get_or_create_user

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db

def _create_user_agent(db, user_agent):
	new_agent = UserAgents(user_agent=user_agent)
	db.session.add(new_agent)
	db.session.flush()
	return new_agent

def _get_user_agent_id(db, user_agent):
	user_agent_record = db.session.query(UserAgents).filter(
										UserAgents.user_agent == user_agent).first()
	if user_agent_record is None:
		user_agent_record = _create_user_agent(db, user_agent)
	return user_agent_record.user_agent_id

def _get_user_agent(user_agent):
	# We have a 512 limit on user agent, truncate if we have to.
	return user_agent[:512] if len(user_agent) > 512 else user_agent

def end_session(user, session_id, timestamp):
	timestamp = timestamp_type(timestamp)
	db = get_analytics_db()

	# Make sure to verify the user/session match up; if possible.
	if user is not None:
		user = get_or_create_user(user)
		uid = user.user_id

		old_session = db.session.query(Sessions).filter(
										Sessions.session_id == session_id,
										Sessions.user_id == uid).first()
	else:
		old_session = db.session.query(Sessions).filter(
										Sessions.session_id == session_id).first()

	result = None

	# Make sure we don't end a session that was already explicitly
	# ended.
	if 		old_session is not None \
		and not old_session.end_time:
		old_session.end_time = timestamp
		result = old_session
	return result

def create_session(user, user_agent, start_time, ip_addr, end_time=None):
	db = get_analytics_db()
	user = get_or_create_user(user)
	uid = user.user_id
	start_time = timestamp_type(start_time)
	end_time = timestamp_type(end_time) if end_time is not None else None
	user_agent = _get_user_agent(user_agent)
	user_agent_id = _get_user_agent_id(db, user_agent)

	new_session = Sessions(user_id=uid,
							start_time=start_time,
							end_time=end_time,
							ip_addr=ip_addr,
							user_agent_id=user_agent_id)

	check_ip_location(db, ip_addr, uid)

	db.session.add(new_session)
	db.session.flush()

	make_transient(new_session)
	return new_session

def get_session_by_id(session_id):
	db = get_analytics_db()
	session_record = db.session.query(Sessions).filter(
									Sessions.session_id == session_id).first()
	if session_record:
		make_transient(session_record)
	return session_record

def _resolve_session(row):
	return row

def get_user_sessions(user, timestamp=None, max_timestamp=None,
                      for_timestamp=None, open_sessions_only=False,
                      query_builder=None):
	"""
	Fetch any sessions for a user started *after* the optionally given timestamp.
	"""
	filters = []
	if timestamp is not None:
		filters.append(Sessions.start_time >= timestamp)

	if max_timestamp is not None:
		filters.append(Sessions.start_time <= max_timestamp)

	if for_timestamp is not None:
		filters.append(Sessions.start_time <= for_timestamp)
		filters.append(Sessions.end_time >= for_timestamp)

	results = get_filtered_records(user, Sessions, filters=filters, query_builder=query_builder)
	return resolve_objects(_resolve_session, results)

def get_recent_user_sessions(user, limit=None):
	def query_builder(query):
		query = query.order_by(Sessions.start_time.desc())
		if limit:
			query = query.limit(limit)
		return query
	return get_user_sessions(user, query_builder=query_builder)


FUZZY_START_DETLA = timedelta(hours=4)
FUZZY_END_DELTA = timedelta(minutes=5)


def get_active_session_count(fuzzy_start_delta=FUZZY_START_DETLA,
                             fuzzy_end_delta=FUZZY_END_DELTA,
                             _now=None):
	"""
	Query sessions that have begun recently (based on fuzzy_start_delta) and
	have not ended or have ended recently (fuzzy_end_delta). The huersitics
	attempt to account for the fact that sometime we don't sessions ended properly.
	"""
	db = get_analytics_db()
	query = db.session.query(Sessions)

	now = _now or datetime.utcnow()

	#If not yet ended, it needs to have been started recently
	started_after = now - fuzzy_start_delta
	not_ended_filter = and_((Sessions.end_time == None), Sessions.start_time >= started_after)

	#or

	#If it ended recently it is active (to deal with heartbeat style updates)
	ended_after = now - fuzzy_end_delta
	ended_recently_filter = (Sessions.end_time >= ended_after)

	query = query.filter(or_(not_ended_filter, ended_recently_filter))

	return query.distinct(Sessions.user_id).count()

