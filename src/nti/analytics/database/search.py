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

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.root_context import get_root_context_record

from nti.analytics.database.users import get_or_create_user

from nti.analytics_database.search import SearchQueries

from nti.dataserver.users import User

from nti.ntiids.ntiids import find_object_with_ntiid

logger = __import__('logging').getLogger(__name__)


def create_search_event(timestamp, session_id, username, elapsed, hit_count, term, search_types, course_id):
	db = get_analytics_db()
	user = User.get_user( username )
	if user is None:
		return

	user_record = get_or_create_user( user )
	timestamp = timestamp_type( timestamp )
	course = find_object_with_ntiid(course_id)
	course_record = None
	if course is not None:
		course_record = get_root_context_record(course, create=True)
	search_types = '/'.join(search_types) if search_types else None

	search = SearchQueries(session_id=session_id,
						   timestamp=timestamp,
						   entity_root_context_id=None, # Not used yet
						   query_elapsed_time=elapsed,
						   hit_count=hit_count,
						   search_types=search_types,
						   term=term)

	search._user_record = user_record
	search._root_context_record = course_record
	db.session.add(search)
	logger.info('Created search event (user=%s) (term=%s)', username, term)
	return user


def _resolve_search_query(row, user=None, course=None):
	if user is not None:
		row.user = user
	if course is not None:
		row.RootContext = course
	return row


def get_search_queries( user=None, course=None, **kwargs ):
	results = get_filtered_records(user, SearchQueries, course=course, **kwargs)
	return resolve_objects(_resolve_search_query, results,
						   user=user, course=course)
