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
from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import externalization

from datetime import datetime

from pyramid.location import lineage

import zope.intid
from zope import component

from nti.utils.property import Lazy

from . import create_job
from . import get_job_queue

from six import integer_types
from six import string_types

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
	result = None
	if 		isinstance( nti_session, string_types ) \
		or 	nti_session is None:
		result = nti_session
	else:
		result = getattr( nti_session, 'session_id', None )

	return result

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
	# TODO Should we fall back and look up by ntiid here?
	return result

# Copied from nti.store.content_utils
def _get_paths(ntiid, library=None, registry=component):
    library = registry.queryUtility(lib_interfaces.IContentPackageLibrary) \
              if library is None else library
    paths = library.pathToNTIID(ntiid) if library and ntiid else ()
    return paths or ()

def _get_collection_root(ntiid, library=None, registry=component):
    paths = _get_paths(ntiid, library, registry)
    return paths[0] if paths else None

def get_course_by_ntiid( ntiid ):
	course = _get_collection_root( ntiid )
	return ICourseInstance( course )


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

class IDLookup(object):
	""" Defines a unique identifier for objects that can be used for storage."""

	@Lazy
	def intids(self):
		return component.getUtility( zope.intid.IIntiIds )

	def get_id_for_object( self, obj ):
		result = getattr( obj, '_ds_intid', None )
		return result or self.intids.getId( obj )

	def get_id_for_user(self, user):
		if not user:
			return None
		# We may already have an integer id, use it.
		if isinstance( user, integer_types ):
			return user
		return self.get_id_for_object( user )

	def get_id_for_session( self, nti_session ):
		# We're likely getting session_ids here, which we will just return.
		return get_id_for_session( nti_session )

	def get_id_for_course( self, course ):
		# ID needs to be unique by semester...
		if isinstance( course, ( integer_types, string_types ) ):
			return course
		return self.get_id_for_object( course )

	def get_id_for_comment(self, comment):
		return self.get_id_for_object( comment )

	def get_id_for_forum(self, forum):
		return self.get_id_for_object( forum )

	def get_id_for_discussion(self, discussion):
		return self.get_id_for_object( discussion )

	def get_id_for_note(self, note):
		return self.get_id_for_object( note )

	def get_id_for_highlight(self, highlight):
		return self.get_id_for_object( highlight )

	def get_id_for_resource(self, resource):
		""" Resource could be a video or content piece. """
		if isinstance( resource, string_types ):
			result = resource
		else:
			result = getattr( resource, 'ntiid', None )
		return result

	def get_id_for_blog(self, blog):
		return self.get_id_for_object( blog )

	def get_id_for_chat(self, chat):
		return self.get_id_for_object( chat )

	def get_id_for_dfl(self, dfl):
		return self.get_id_for_object( dfl )

	def get_id_for_friends_list(self, friends_list):
		return self.get_id_for_object( friends_list )

	def get_id_for_submission(self, submission):
		return self.get_id_for_object( submission )

	def get_id_for_feedback(self, feedback):
		return self.get_id_for_object( feedback )
