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

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.indexed_data.interfaces import IAudioIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer

from nti.site import site

from nti.externalization import externalization

from datetime import datetime

from pyramid.location import lineage

from zope import component
from zope.component.hooks import site as current_site
from zope.traversing.interfaces import IEtcNamespace

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

# Copied from digest_email
# Really expensive: 1s/call in local testing in which the worst case occurred frequently.
def _path_to_ugd_container(name):
	__traceback_info__ = name
	assert name.startswith('tag:')

	# Try to find a content unit, in decreasing order of chance
	lib = component.getUtility(IContentPackageLibrary)
	path = lib.pathToNTIID(name)
	if path:
		return path

	ifaces = (IAudioIndexedDataContainer,IVideoIndexedDataContainer)
	def _search(unit):
		for iface in ifaces:
			if iface(unit).contains_data_item_with_ntiid(name):
				return lib.pathToNTIID(unit.ntiid)
		for child in unit.children:
			r = _search(child)
			if r:
				return r

	for package in lib.contentPackages:
		r = _search(package)
		if r:
			return r
	paths = lib.pathsToEmbeddedNTIID(name)
	if paths:
		return paths[0]

def _do_get_course_by_ntiid(name):
	"Return an arbitrary course associated with the content ntiid"
	path = _path_to_ugd_container(name)
	__traceback_info__ = path
	if path:
		course = None
		for unit in reversed(path):
			# The adapter function here is where the arbitraryness
			# comes in
			course = ICourseInstance( unit, None )
			if course is not None:
				return course

def get_course_by_ntiid(name):
	# Some content is only accessible from the global content
	# package.  During migration, we'll need to (in most cases)
	# check there first, before falling back to checking our current
	# site.  Once the migration is complete, we should default to
	# our current site in the fast lane.
	# This is expensive if we do not find our course.

	# Is there a better way to do this?
	host_sites = component.getUtility(IEtcNamespace, name='hostsites')
	ds_folder = host_sites.__parent__
	ds_site_manager = ds_folder.getSiteManager()
	my_site = site.getSite()

	result = None

	if my_site.getSiteManager() != ds_site_manager:
		global_site = my_site.__parent__.__parent__
		with current_site(global_site):
			result = _do_get_course_by_ntiid(name)

	if result is None:
		# Try our current site
		result = _do_get_course_by_ntiid(name)

	if result is None:
		raise TypeError( "No course found for containerId (%s)" % name )
	return result

def _execute_job( *args, **kwargs ):
	# This is our merging solution.  String parse the error message
	# to detect mysql-only 'Duplicate entry' remarks.  We cannot
	# use sqlalchemy merge because most of our primary keys are
	# sequences.  We cannot use the dataserver ids as primary keys
	# since they may be reused.  Another option would be to manually
	# read query the db to see if a duplicate record exists before
	# insert.  However, since this should only occur during the small
	# migration window (populating the queues with everything from
	# the dataserver db: ~10 minutes with PROD DB locally), let us
	# go with this approach.
	db = get_analytics_db()

	args = BList( args )
	func = args.pop( 0 )

	sp = db.savepoint()
	try:
		func( *args, **kwargs )
		# Must flush to verify integrity
		db.session.flush()
	except IntegrityError as e:
		vals = e.orig.args
		# MySQL only
		if 'Duplicate entry' in vals[1]:
			# Ok duplicate entry, lets ignore these since we likely
			# already have this record stored.
			logger.info( 	'Duplicate entry found, will ignore (%s) (%s)',
							func, kwargs )
			if sp is not None:
				sp.rollback()
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
