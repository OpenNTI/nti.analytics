#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from collections import OrderedDict

from nti.contenttypes.courses.interfaces import ICourseSubInstance

from nti.dataserver.interfaces import IEntity

from nti.analytics.read_models import AnalyticsLike
from nti.analytics.read_models import AnalyticsFavorite

from . import get_analytics_db

from .users import get_user
from .users import get_user_db_id
from .users import get_or_create_user

from .root_context import get_root_context
from .root_context import get_root_context_id

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

def get_root_context_ids( root_context ):
	course_id = entity_root_context_id = None
	if IEntity.providedBy( root_context ):
		entity = get_or_create_user( root_context )
		entity_root_context_id = entity.user_id
	else:
		db = get_analytics_db()
		course_id = get_root_context_id( db, root_context, create=True )
	return course_id, entity_root_context_id

def get_root_context_obj( root_context_record ):
	course_id = root_context_record.course_id
	if course_id:
		root_context = get_root_context( course_id )
	else:
		entity_root_context_id = root_context_record.entity_root_context_id
		root_context = get_user( entity_root_context_id )
	return root_context

def _do_course_and_timestamp_filtering( table, timestamp=None, max_timestamp=None, course=None, filters=None ):
	db = get_analytics_db()
	result = []

	if course is not None:
		course_id = get_root_context_id( db, course )
		course_ids = [ course_id ]

		# For courses with super-instances (e.g. History)
		# we want to aggregate any data that may have been
		# pinned on the super instance as well. I think we
		# would want this for any scenario.
		if ICourseSubInstance.providedBy( course ):
			parent = course.__parent__.__parent__
			parent_id = get_root_context_id( db, parent )
			course_ids.append( parent_id )

		if course_ids:
			filters.append( table.course_id.in_( course_ids ) )
		else:
			# If we have a course, but no course_id (return empty)
			return result

	if timestamp is not None:
		filters.append( table.timestamp >= timestamp )

	if max_timestamp is not None:
		filters.append( table.timestamp <= max_timestamp )

	result = db.session.query( table ).filter( *filters ).all()

	return result

def get_filtered_records( user, table, replies_only=False, filters=None, **kwargs ):
	"""
	Get the filtered records for the given user, table, timestamp (and course).
	"""
	result = []
	filters = list( filters ) if filters else []

	if user is not None:
		user_id = get_user_db_id( user )
		if user_id is not None:
			filters.append( table.user_id == user_id )
		else:
			# If we have a user, but no user_id (return empty)
			return result

	if replies_only:
		filters.append( table.parent_user_id != None )

	result = _do_course_and_timestamp_filtering( table, filters=filters, **kwargs )
	return result

def get_user_replies_to_others( table, user, get_deleted=False, filters=None, **kwargs ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	user_id = get_user_db_id( user )

	filters = [] if filters is None else list(filters)
	filters.append( table.parent_user_id != user_id )

	if not get_deleted:
		filters.append( table.deleted == None )

	return get_filtered_records( user, table, filters=filters, **kwargs )

def get_replies_to_user( table, user,get_deleted=False, **kwargs  ):
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
		result = _do_course_and_timestamp_filtering( table, filters=filters, **kwargs )

	return result

def get_ratings_for_user_objects( table, user, **kwargs ):
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
		result = _do_course_and_timestamp_filtering( table, filters=filters, **kwargs )

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
