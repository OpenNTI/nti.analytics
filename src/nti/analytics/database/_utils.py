#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
from nti.analytics.database.root_context import get_root_context_id
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import OrderedDict

from nti.analytics.read_models import AnalyticsLike
from nti.analytics.read_models import AnalyticsFavorite

from . import get_analytics_db

from .users import get_user
from .users import get_user_db_id

def get_context_path( context_path ):
	# Note: we could also sub these resource_ids for the actual
	# ids off of the Resources table.  That would be a bit tricky, because
	# we sometimes have courses and client specific strings (e.g. 'overview')
	# in this collection.

	result = ''
	if context_path:
		# This will remove all duplicate elements. Hopefully we do
		# not have scattered duplicates, which would be an error condition.
		context_path = list( OrderedDict.fromkeys( context_path ) )
		# '/' is illegal in ntiid strings
		result = '/'.join( context_path )

	return result

def expand_context_path( context_path ):
	return context_path.split( '/' )

def _do_course_and_timestamp_filtering( table, timestamp=None, course=None, filters=None ):
	db = get_analytics_db()
	result = []

	if course is not None:
		course_id = get_root_context_id( db, course )
		if course_id is not None:
			filters.append( table.course_id == course_id )
		else:
			# If we have course, but no course_id (return empty)
			return result

	if timestamp is not None:
		filters.append( table.timestamp >= timestamp )

	result = db.session.query( table ).filter( *filters ).all()

	return result

def get_filtered_records( user, table, timestamp=None, course=None, filters=None ):
	"""
	Get the filtered records for the given user, table, timestamp (and course).
	"""
	result = []
	user_id = get_user_db_id( user )

	if user_id is not None:
		filters = list( filters ) if filters else []
		filters.append( table.user_id == user_id )

		result = _do_course_and_timestamp_filtering( table, timestamp, course, filters )
	return result

def get_user_replies_to_others( table, user, course=None, timestamp=None, get_deleted=False, filters=None ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	user_id = get_user_db_id( user )

	filters = [] if filters is None else list(filters)
	filters.extend( ( table.parent_user_id is not None,
					table.parent_user_id != user_id ) )

	if not get_deleted:
		filters.append( table.deleted == None )

	return get_filtered_records( user, table, course=course,
								timestamp=timestamp, filters=filters )

def get_replies_to_user( table, user, course=None, timestamp=None, get_deleted=False  ):
	"""
	Fetch any replies to our user, *after* the optionally given timestamp.
	"""
	# This is similar to our generic filtering func above, but
	# we want to specifically exclude our given user.
	result = []
	user_id = get_user_db_id( user )
	filters = [ table.parent_user_id == user_id,
				table.user_id != user_id ]

	if not get_deleted:
		filters.append( table.deleted == None )

	if user_id is not None:
		result = _do_course_and_timestamp_filtering( table, timestamp, course, filters )

	return result

def get_ratings_for_user_objects( table, user, course=None, timestamp=None ):
	"""
	Fetch any ratings for a user's objects, optionally filtering by date,
	course.
	"""
	# This is similar to our generic filtering func above, but
	# we want to specifically exclude our given user.
	result = []
	user_id = get_user_db_id( user )
	# Do we want to exclude any self-favorites/likes?
	filters = [ table.creator_id == user_id ]

	if user_id is not None:
		result = _do_course_and_timestamp_filtering( table, timestamp, course, filters )

	return result

def _do_resolve_rating( clazz, row, rater, obj_creator ):
	user = get_user( row.user_id ) if rater is None else rater
	creator = get_user( row.creator_id ) if obj_creator is None else obj_creator

	result = None
	if		user is not None \
		and creator is not None:
		result = clazz(	user=user,
						timestamp=row.timestamp,
						ObjectCreator=creator )
	return result

def resolve_like( row, rater=None, obj_creator=None ):
	return _do_resolve_rating( AnalyticsLike, row, rater, obj_creator )

def resolve_favorite( row, rater=None, obj_creator=None ):
	return _do_resolve_rating( AnalyticsFavorite, row, rater, obj_creator )
