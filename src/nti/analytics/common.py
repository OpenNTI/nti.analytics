#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from ZODB.POSException import POSKeyError

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.indexed_data.interfaces import IAudioIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer

from nti.externalization import externalization

from datetime import datetime

from pyramid.location import lineage

import zope.intid
from zope import component

from . import create_job
from . import get_job_queue

from six import integer_types

from nti.analytics.identifier import SessionId
_sessionid = SessionId()

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

def get_nti_session( user ):
	""" Attempt to get the current session for the user, returning None if none found. """
	session_storage = component.getUtility( nti_interfaces.ISessionServiceStorage )
	sessions = session_storage.get_sessions_by_owner( user )
	# We may have multiple; grab the first.
	# See note in session_storage on why this may no longer be necessary.
	nti_session = next( sessions, None )
	return nti_session

def get_nti_session_id( user ):
	""" Attempt to get the current session id for the user, returning None if none found. """
	nti_session = None
	try:
		nti_session = get_nti_session( user )
	except TypeError:
		# Some cases (creating Forums as community) won't let us
		# get a session.
		logger.debug( 'Failed to get session for user (%s)', user )
	return get_id_for_session( nti_session )

def get_id_for_session( nti_session ):
	""" Given an nti_session, return the unique id """
	return _sessionid.get_id( nti_session )

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

def get_course_by_ntiid(name):
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
	raise TypeError( "No course found for path (%s)" % path )

def process_event( object_op, obj=None, **kwargs ):
	effective_kwargs = kwargs
	if obj is not None:
		# If we have an object, grab its ID by default.
		oid = to_external_ntiid_oid( obj )
		effective_kwargs = dict( kwargs )
		effective_kwargs['oid'] = oid

	queue = get_job_queue()
	job = create_job( object_op, **effective_kwargs )
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
