#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.intid import interfaces as intid_interfaces
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from .common import get_creator
from .common import to_external_ntiid_oid

from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import relationships
from . import interfaces as graph_interfaces

def _add_created_relationship(db, oid, creator):
	obj = ntiids.find_object_with_ntiid(oid)
	creator = Entity.get_entity(creator)
	if obj is not None and creator is not None:
		result = db.create_relationship(creator, obj, relationships.Created())
		if result is not None:
			logger.debug("creator relationship %s retreived/created", result)
			return True
	return False

def _process_created_event(db, created):
	creator = get_creator(created)
	if creator:
		oid = to_external_ntiid_oid(created)
		queue = get_job_queue()
		job = create_job(_add_created_relationship, db=db, oid=oid,
						 creator=creator.username)
		queue.put(job)

@component.adapter(nti_interfaces.ICreated, lce_interfaces.IObjectCreatedEvent)
def _object_created(created, event):
	db = get_graph_db()
	if db is not None:
		_process_created_event(db, created)

@component.adapter(chat_interfaces.IMessageInfoPostedToRoomEvent)
def _message_posted_to_room(event):
	db = get_graph_db()
	if db is not None:
		_process_created_event(db, event.object)

def _update_created(db, oid):
	created = ntiids.find_object_with_ntiid(oid)
	adapted = graph_interfaces.IUniqueAttributeAdapter(created, None)
	if adapted is not None and adapted.key and adapted.value and created is not None:
		node = db.get_indexed_node(adapted.key, adapted.value)
		if node is not None:
			labels = graph_interfaces.ILabelAdapter(created)
			properties = graph_interfaces.IPropertyAdapter(created)
			db.update_node(node, labels, properties)
			logger.debug("properties updated for node %s", node)

def _process_created_modified(db, created):
	oid = to_external_ntiid_oid(created)
	queue = get_job_queue()
	job = create_job(_update_created, db=db, oid=oid)
	queue.put(job)

@component.adapter(nti_interfaces.ICreated, lce_interfaces.IObjectModifiedEvent)
def _object_modified(created, event):
	db = get_graph_db()
	if db is not None:
		_process_created_modified(db, created)

def _remove_node(db, key, value):
	node = db.get_indexed_node(key, value)
	if node is not None:
		db.delete_node(node)
		logger.debug("node %s deleted", node)
		return True
	return False

def _process_created_removed(db, created):
	adapted = graph_interfaces.IUniqueAttributeAdapter(created, None)
	if adapted is not None and adapted.key and adapted.value:
		queue = get_job_queue()
		job = create_job(_remove_node, db=db, key=adapted.key, value=adapted.value)
		queue.put(job)

@component.adapter(nti_interfaces.ICreated, intid_interfaces.IIntIdRemovedEvent)
def _object_removed(created, event):
	db = get_graph_db()
	if db is not None:
		_process_created_removed(db, created)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if 	nti_interfaces.ICreated.providedBy(obj) or \
		chat_interfaces.IMessageInfo.providedBy(obj):
		_process_created_event(db, obj)
		result = True
	return result
