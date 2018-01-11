#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from pyramid.threadlocal import get_current_request

from pyramid.traversal import find_interface

from six import integer_types

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.intid.interfaces import IntIdMissingError
from zope.intid.interfaces import ObjectMissingError

from ZODB.POSException import POSError

from nti.asynchronous import create_job

from nti.analytics.database import get_analytics_db

from nti.analytics.interfaces import IPriorityProcessingAnalyticsEvent

from nti.dataserver import liking
from nti.dataserver import rating

from nti.dataserver.interfaces import IEntity

from nti.dataserver.rating import IObjectUnratedEvent

from nti.dataserver.users import Entity

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IGlobalFlagStorage

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.ntiids import oids

from nti.securitypolicy.utils import is_impersonating

from nti.site.site import get_site_for_site_names

from nti.site.transient import TrivialSite


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
	flag_storage = component.queryUtility( IGlobalFlagStorage )
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
	if not IEntity.providedBy(entity):
		entity = Entity.get_entity(str(entity))
	return entity

def get_creator(obj):
	try:
		creator = getattr(obj, 'creator', None)
		creator = get_entity(creator) if creator else None
		return creator
	except (TypeError, POSError):
		return None

def get_deleted_time( obj ):
	# Try for last modified, otherwise take whatever time we have now
	deleted_time = getattr( obj, 'lastModified', datetime.utcnow() )
	return deleted_time

def to_external_ntiid_oid(obj):
	ntiid = oids.to_external_ntiid_oid(obj) if obj is not None else None
	parts = ntiid.split(":") if ntiid else ()
	if len(parts) > 4:  # check if intid is in the oid
		ntiid = ':'.join(parts[:4])
	return ntiid

def get_object_root( obj, type_to_find ):
	"""
	Work up the parent tree looking for 'type_to_find', returning None if not found.
	"""
	return find_interface( obj, type_to_find )

def get_course( obj ):
	"""
	Attempt to get the course of an object by traversing up the given
	object's lineage.
	"""
	result = get_object_root( obj, ICourseInstance )
	__traceback_info__ = result, obj
	return ICourseInstance( result, result )

def get_created_timestamp(obj):
	result = getattr( obj, 'createdTime', None )
	result = result or datetime.utcnow()
	result = timestamp_type( result )
	return result

def timestamp_type(timestamp):
	result = timestamp
	if isinstance( timestamp, ( float, integer_types ) ):

		# We fully expect fractional seconds; if not, we attempt to handle it.
		ts_string = str( int( timestamp ) )
		if len( ts_string ) > 12:
			logger.warn('Timestamp received in ms, converting to seconds (%s)',
						timestamp )
			timestamp = timestamp / 1000.0
		result = datetime.utcfromtimestamp( timestamp )

	if result:
		# Mysql drops milliseconds
		result = result.replace( microsecond=0 )
	return result

def get_root_context_name(context):
	"""
	Try to fetch a human readable name for the given context.
	"""
	cat_entry = ICourseCatalogEntry( context, None )
	context_name = getattr(cat_entry, 'ProviderUniqueID', '')
	if not context_name:
		# content package
		context_name = getattr(context, 'title', '')
	if not context_name:
		# Not ideal
		context_name = getattr(context, '__name__', '')
	return context_name

def _do_execute_job( db, *args, **kwargs ):
	func, args = args[0], args[1:]
	try:
		result = func( *args, **kwargs )
	except ( IntIdMissingError, ObjectMissingError ) as e:
		# Nothing we can do with these events; leave them on the floor.
		logger.info(
			'Object missing (deleted) before event could be processed; event dropped. (%s) (%s)',
			e, func )
		result = None
	else:
		# Must flush to verify integrity.  If we hit any race
		# conditions below, this will raise and the job can
		# be re-run.
		db.session.flush()
	return result

def _execute_job( *args, **kwargs ):
	"""
	Performs the actual execution of a job.  We'll attempt to do
	so in the site the event occurred in, otherwise, we'll run in
	whatever site we are currently in.
	"""
	event_site_name = kwargs.pop( 'site_name', None )
	old_site = getSite()

	# Find the site to run in
	if event_site_name is None:
		logger.warn( 'Event does not have site_name, will run in default site' )
		event_site = old_site
	else:
		# Need to use root site to access the given site.
		dataserver = component.getUtility( IDataserver )
		ds_folder = dataserver.root_folder['dataserver2']

		with current_site( ds_folder ):
			event_site = get_site_for_site_names( (event_site_name,) )

		if 		event_site is None \
			or 	isinstance( event_site, TrivialSite ):
			# We could get a trivial site, which is unlikely to be useful.
			raise ValueError( 'No site found for (%s)' % event_site_name )

	with current_site( event_site ):
		# We bail if our site does not have a db.
		db = get_analytics_db( strict=False )
		if db is None:
			logger.info( 'No analytics db found for site (%s), will drop event',
						 event_site_name )
			return None

		return _do_execute_job( db, *args, **kwargs )


def should_create_analytics(request):
	"""
	Decides if this request should create analytics data.
	"""
	# Is our user impersonating?
	if is_impersonating(request):
		logger.info('Not creating analytics data for impersonating user (%s)',
					request.remote_user)
		return False
	return True


def process_event( get_job_queue, object_op, obj=None, immediate=False, **kwargs ):
	"""
	Processes the event, which may not occur synchronously.
	"""
	# We could check if we have analytics for this site before queuing the event.
	request = get_current_request()
	if not should_create_analytics( request ):
		return

	effective_kwargs = dict( kwargs )
	if obj is not None:
		# If we have an object, grab its ID by default.
		oid = to_external_ntiid_oid( obj )
		effective_kwargs['oid'] = oid

	# Now tag our event with the current site
	cur_site = getSite()
	if cur_site is not None:
		effective_kwargs['site_name'] = cur_site.__name__
	else:
		logger.warn( 'Request did not have site (%s)', request )

	event = effective_kwargs.get('event')
	if immediate or IPriorityProcessingAnalyticsEvent.providedBy(event):
		_execute_job( object_op, **effective_kwargs )
	else:
		queue = get_job_queue()
		job = create_job( _execute_job, object_op, **effective_kwargs )
		queue.put( job )
