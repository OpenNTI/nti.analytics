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

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import ResourceId

from . import get_analytics_db
from . import should_update_event
from .users import get_user_db_id
from .users import get_or_create_user
from .resources import get_resource_id

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

def _resource_view_exists( db, table, user_id, resource_id, timestamp ):
	return db.session.query( table ).filter(
							table.user_id == user_id,
							table.resource_id == resource_id,
							table.timestamp == timestamp ).first()

def create_view( table, user, nti_session, timestamp, course, context_path, resource, time_length):
	"""
	Create a basic view event, if necessary.  Also if necessary, may update existing
	events with appropriate data.
	"""
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	rid = ResourceId.get_id( resource )
	rid = get_resource_id( db, rid, create=True )

	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	existing_record = _resource_view_exists( db, table, uid, rid, timestamp )
	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
			return
		else:
			logger.warn( '%s view already exists (user=%s) (resource_id=%s) (timestamp=%s)',
						table.__tablename__, user, rid, timestamp )
			return
	context_path = get_context_path( context_path )

	new_object = table( user_id=uid,
						session_id=sid,
						timestamp=timestamp,
						course_id=course_id,
						context_path=context_path,
						resource_id=rid,
						time_length=time_length )
	db.session.add( new_object )

def get_filtered_records( user, table, timestamp=None, course=None, filters=None ):
	"""
	Get the filtered records for the given user, table, timestamp (and course).
	"""
	db = get_analytics_db()
	result = []
	user_id = get_user_db_id( user )

	if user_id is not None:
		filters = list( filters ) if filters else []
		filters.append( table.user_id == user_id )

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

def get_user_replies_to_others( table, user, course=None, timestamp=None, get_deleted=False ):
	"""
	Fetch any replies our users provided, *after* the optionally given timestamp.
	"""
	user_id = get_user_db_id( user )
	filters = [ table.parent_user_id is not None,
				table.parent_user_id != user_id ]

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
	db = get_analytics_db()
	result = []
	user_id = get_user_db_id( user )
	filters = [ table.parent_user_id == user_id,
				table.user_id != user_id ]

	if not get_deleted:
		filters.append( table.deleted == None )

	if user_id is not None:
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
