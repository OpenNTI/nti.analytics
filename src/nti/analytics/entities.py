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

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from .common import to_external_ntiid_oid

from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import interfaces as graph_interfaces

def _remove_entity(db, key, value):
	node = db.get_indexed_node(key, value)
	if node is not None:
		db.delete_node(node)
		logger.debug("node %s deleted", node)
		return True
	return False

def _add_entity(db, oid):
	entity = ntiids.find_object_with_ntiid(oid)
	if entity is not None:
		node = db.get_or_create_node(entity)
		logger.debug("entity node %s created/retrieved", node)
		return entity, node
	return None, None

def _process_entity_removed(db, entity):
	adapted = graph_interfaces.IUniqueAttributeAdapter(entity)
	queue = get_job_queue()
	job = create_job(_remove_entity,
					 db=db,
					 key=adapted.key,
					 value=adapted.value)
	queue.put(job)

def _process_entity_added(db, entity):
	oid = to_external_ntiid_oid(entity)
	queue = get_job_queue()
	job = create_job(_add_entity, db=db, oid=oid)
	queue.put(job)

@component.adapter(nti_interfaces.IEntity, lce_interfaces.IObjectAddedEvent)
def _entity_added(entity, event):
	db = get_graph_db()
	queue = get_job_queue()
	if 	db is not None and queue is not None:  # check queue b/c of Everyone comm
		_process_entity_added(db, entity)

@component.adapter(nti_interfaces.IEntity, intid_interfaces.IIntIdRemovedEvent)
def _entity_removed(entity, event):
	db = get_graph_db()
	if db is not None:
		_process_entity_removed(db, entity)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if nti_interfaces.IEntity.providedBy(obj) and \
		not nti_interfaces.IFriendsList.providedBy(obj):
		_process_entity_added(db, obj)
		result = True
	return result
