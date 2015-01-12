#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from pyramid.location import lineage
from pyramid.threadlocal import get_current_request

from six import integer_types

from zope import component
from zope.component.hooks import site as current_site
from zope.component.hooks import getSite

from zc.blist import BList

from ZODB.POSException import POSKeyError

from nti.async import create_job

from nti.analytics.database import get_analytics_db

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import rating
from nti.dataserver import liking
from nti.dataserver.rating import IObjectUnratedEvent
from nti.dataserver.users import Entity

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IGlobalFlagStorage

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.externalization import externalization

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

def get_object_root( obj, type_to_find ):
	""" Work up the parent tree looking for 'type_to_find', returning None if not found. """
	result = None
	for location in lineage( obj ):
		candidate = type_to_find( location, None )
		if candidate is not None:
			result = candidate
			break
	return result

def get_course( obj ):
	"""
	Attempt to get the course of an object by traversing up the given
	object's lineage.
	"""
	# TODO We call this for topics; will topics exist in books?
	# If so, this needs to change.
	result = get_object_root( obj, ICourseInstance )
	__traceback_info__ = result, obj
	return ICourseInstance( result )

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
		# TODO This does not seem to occur in other code paths
		# that pull a site by name.
		dataserver = component.getUtility( IDataserver )
		ds_folder = dataserver.root_folder['dataserver2']

		with current_site( ds_folder ):
			event_site = get_site_for_site_names( (event_site_name,) )

		if 		event_site is None \
			or 	isinstance( event_site, TrivialSite ):
			# We could get a trival site, which is unlikely to be
			# useful.
			raise ValueError( 'No site found for (%s)' % event_site_name )

	with current_site( event_site ):
		# We bail if our site does not have a db.
		db = get_analytics_db()
		if db is None:
			logger.info( 'No analytics db found for site (%s), will drop event',
						event_site_name )
			return

		args = BList( args )
		func = args.pop( 0 )

		result = func( *args, **kwargs )
		# Must flush to verify integrity.  If we hit any race
		# conditions below, this will raise and the job can
		# be re-run.
		db.session.flush()
		return result

def _should_create_analytics( request ):
	"Decides if this request should create analytics data."
	# Is our user impersonating?
	environ = getattr( request, 'environ', () )
	if 'REMOTE_USER_DATA' in environ and environ['REMOTE_USER_DATA']:
		logger.info( 'Not creating analytics data for impersonating user (%s)',
					request.remote_user )
		return False
	return True

def process_event( get_job_queue, object_op, obj=None, **kwargs ):
	"""
	Processes the event, which may not occur synchronously.
	"""
	# TODO Do we want to check if we have analytics
	# for this site before queuing the event?

	request = get_current_request()
	if not _should_create_analytics( request ):
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

	queue = get_job_queue()
	job = create_job( _execute_job, object_op, **effective_kwargs )
	queue.put( job )

def get_created_timestamp(obj):
	result = getattr( obj, 'createdTime', None )
	result = result or datetime.utcnow()
	result = timestamp_type( result )
	return result

def timestamp_type(timestamp):
	result = timestamp
	if isinstance( timestamp, ( float, integer_types ) ):
		result = datetime.utcfromtimestamp( timestamp )

	if result:
		# Mysql drops milliseconds
		result = result.replace( microsecond=0 )
	return result

def get_root_context_name(course):
	cat_entry = ICourseCatalogEntry( course, None )
	course_name = getattr( cat_entry, 'ProviderUniqueID',
						getattr( course, '__name__', None ) )
	return course_name

