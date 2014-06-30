#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids
from nti.intid import interfaces as intid_interfaces

from .common import process_event

from . import create_job
from . import get_job_queue
from . import interfaces as analytics_interfaces

def _add_entity(db, oid):
	entity = ntiids.find_object_with_ntiid(oid)
	if entity is not None:
		db.create_user( entity )
		logger.debug( "User created (%s)", entity )

# Note: We are not handling entity removal. I'm not sure we need to.

@component.adapter(nti_interfaces.IEntity, intid_interfaces.IIntIdAddedEvent)
def _entity_added(entity, event):
	# TODO We only want users here right? What's the inclusive check?
 	queue = get_job_queue()
 	# During nti.dataserver generations, the Everyone entity is installed (?)
 	# and an event is fired, which we cannot handle yet because our evolving
 	# has not yet occurred; but that's ok.
	if 		not nti_interfaces.IFriendsList.providedBy( entity ) \
		and queue is not None:
		process_event( _add_entity, entity )

component.moduleProvides(analytics_interfaces.IObjectProcessor)
def init( obj ):
	result = False
	if 	nti_interfaces.IEntity.providedBy(obj) and \
		not nti_interfaces.IFriendsList.providedBy(obj):
		process_event( _add_entity, obj )
		result = True
	return result
