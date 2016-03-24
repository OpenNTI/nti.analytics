#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics.common import timestamp_type

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database.users import get_or_create_user

from nti.analytics_database.search import SearchQueries

from nti.dataserver.users import User

from nti.ntiids.ntiids import find_object_with_ntiid

def create_search_event( timestamp, session_id, username, elapsed, hit_count, term, search_types, course_id ):
	db = get_analytics_db()
	user = User.get_user( username )
	if user is None:
		return

	user_record = get_or_create_user( user )
	user_id = user_record.user_id
	timestamp = timestamp_type( timestamp )
	course = find_object_with_ntiid( course_id )
	course_id = get_root_context_id( db, course ) if course is not None else course
	search_types = '/'.join(search_types) if search_types else None

	user = SearchQueries(user_id=user_id,
						session_id=session_id,
						timestamp=timestamp,
						course_id=course_id,
						entity_root_context_id=None, # Not used yet
						query_elapsed_time=elapsed,
						hit_count=hit_count,
						search_types=search_types,
						term=term )

	db.session.add(user)
	db.session.flush()
	logger.info('Created search event (user=%s) (term=%s)', username, term)
	return user

def _resolve_search_query(row, user=None, course=None):
	if user is not None:
		row.user = user
	if course is not None:
		row.RootContext = course
	return row

def get_search_queries( user=None, course=None, **kwargs ):
	results = get_filtered_records( user, SearchQueries, course=course, **kwargs )
	return resolve_objects( _resolve_search_query, results, user=user, course=course )
