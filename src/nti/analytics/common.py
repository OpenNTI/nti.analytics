#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from ZODB.POSException import POSKeyError

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import rating
from nti.dataserver import liking
from nti.dataserver.rating import IObjectUnratedEvent
from nti.dataserver.users import Entity

from nti.dataserver.interfaces import IGlobalFlagStorage

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.externalization import externalization

from datetime import datetime

from pyramid.location import lineage

from zope import component

from zc.blist import BList

from nti.async import create_job
from six import integer_types

from sqlalchemy.exc import IntegrityError
from nti.analytics.database import get_analytics_db

def get_rating_from_event( event ):
	delta = -1 if IObjectUnratedEvent.providedBy( event ) else 1
	is_favorite = None
	if event.category == 'favorites':
		is_favorite = True
	elif event.category == 'likes':
		is_favorite = False
	return is_favorite, delta

def get_likes( obj ):
	return liking.like_count( obj )

def get_favorites( obj ):
	return rating.rate_count( obj, 'favorites')

def get_flagged( obj ):
	flag_storage = component.queryUtility( IGlobalFlagStorage, None )
	result = False
	if flag_storage is not None:
		result = flag_storage.is_flagged( obj )
	return result

def get_ratings( obj ):
	like_count = get_likes( obj )
	favorite_count = get_favorites( obj )
	is_flagged = get_flagged( obj )
	return like_count, favorite_count, is_flagged

def get_entity(entity):
	if not nti_interfaces.IEntity.providedBy(entity):
		entity = Entity.get_entity(str(entity))
	return entity

def get_creator(obj):
	try:
		creator = getattr(obj, 'creator', None)
		creator = get_entity(creator) if creator else None
		return creator
	except (TypeError, POSKeyError):
		return None

def get_object_root( obj, type_to_find ):
	""" Work up the parent tree looking for 'type_to_find', returning None if not found. """
	result = None
	for location in lineage( obj ):
		candidate = type_to_find( location, None )
		if candidate is not None:
			result = candidate
			break
	return result

def get_deleted_time( obj ):
	# Try for last modified, otherwise take whatever time we have now
	deleted_time = getattr( obj, 'lastModified', datetime.utcnow() )
	return deleted_time

def to_external_ntiid_oid(obj):
	ntiid = externalization.to_external_ntiid_oid(obj) if obj is not None else None
	parts = ntiid.split(":") if ntiid else ()
	if len(parts) > 4:  # check if intid is in the oid
		ntiid = ':'.join(parts[:4])
	return ntiid

def get_course( obj ):
	result = get_object_root( obj, ICourseInstance )
	__traceback_info__ = result, obj
	return ICourseInstance( result )

def _execute_job( *args, **kwargs ):
	# 	db = get_analytics_db()
	#
	# 	args = BList( args )
	# 	func = args.pop( 0 )
	#
	# 	func( *args, **kwargs )
	# 	# Must flush to verify integrity.  If we hit any race
	# 	# conditions below, this will raise and the job can
	# 	# be re-run.
	# 	db.session.flush()

	# Temporarily remove duplicates due to migration.
	db = get_analytics_db()

	args = BList( args )
	func = args.pop( 0 )

	sp = db.savepoint()
	try:
		func( *args, **kwargs )
		# Must flush to verify integrity
		db.session.flush()
	except IntegrityError as e:
		if sp is not None:
			sp.rollback()

		vals = e.orig.args
		# MySQL
		if len( vals ) > 1 and 'Duplicate entry' in vals[1]:
			# Duplicate entry, let's ignore these since we likely
			# already have this record stored.
			logger.info('Duplicate entry found, will ignore (%s) (%s)',
						func, kwargs )
		else:
			raise e


def process_event( get_job_queue, object_op, obj=None, **kwargs ):
	effective_kwargs = kwargs
	if obj is not None:
		# If we have an object, grab its ID by default.
		oid = to_external_ntiid_oid( obj )
		effective_kwargs = dict( kwargs )
		effective_kwargs['oid'] = oid

	queue = get_job_queue()
	job = create_job( _execute_job, object_op, **effective_kwargs )
	queue.put( job )

def get_created_timestamp(obj):
	result = getattr( obj, 'createdTime', None )
	result = timestamp_type( result )
	return result or datetime.utcnow()

def timestamp_type(timestamp):
	result = timestamp
	if isinstance( timestamp, ( float, integer_types ) ):
		result = datetime.utcfromtimestamp( timestamp )
	return result

def get_course_name(course):
	cat_entry = ICourseCatalogEntry( course, None )
	course_name = getattr( cat_entry, 'ProviderUniqueID', getattr( course, '__name__', None ) )
	return course_name
