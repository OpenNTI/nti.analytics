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

from nti.externalization import externalization

from datetime import datetime

from pyramid.location import lineage

import zope.intid
from zope import component

from . import create_job
from . import get_job_queue

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
       
def get_nti_session():
	# FIXME Need this
	return None

def get_comment_root( comment, type ):
	""" Work up the comment parent tree looking for 'type', returning None if not found. """
	result = None
	obj = comment
	while obj:
		obj = getattr( obj, '__parent__', None )
		if type.providedBy( obj ):
			result = obj
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
	result = None
	for location in lineage( obj ):
		result = ICourseInstance( location, None )
		if result is not None:
			break
	return result

def process_event( object_op, obj=None, **kwargs ):
	oid = to_external_ntiid_oid( obj )
	queue = get_job_queue()
	job = create_job( object_op, oid=oid, **kwargs )
	queue.put( job )
	
def get_created_timestamp(obj):
	result = getattr( obj, 'createdTime', None )
	result = timestamp_type( result )
	return result or datetime.utcnow()	
	
def timestamp_type(timestamp):
	result = timestamp
	if isinstance( timestamp, float ):
		result = datetime.utcfromtimestamp( timestamp )
	return result	

class IDLookup(object):
	""" Defines a unique identifier for objects that can be used for storage."""	
	
	def __init__( self ):
		self.intids = component.getUtility(zope.intid.IIntIds)
		
	def get_id_for_object( self, obj ):
		result = getattr( obj, '_ds_intid', None )
		return result or self.intids.getId( obj )
	