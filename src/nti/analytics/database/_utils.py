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

from . import get_analytics_db
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

def get_filtered_records( user, table, timestamp=None, course=None, filters=None ):
	"""
	Get the filtered records for the give user, table, timestamp (and course).
	"""
	db = get_analytics_db()
	result = []
	user_id = get_user_db_id( user )
	course_id = None

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
