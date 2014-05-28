#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.intid import interfaces as intid_interfaces
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from .common import to_external_ntiid_oid

from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import relationships
from . import interfaces as graph_interfaces

@interface.implementer(graph_interfaces.IContainer)
class Container(object):
	
	__slots__ = ('id',)

	def __init__(self, containerId):
		self.id = containerId

	@property
	def containerId(self):
		return self.id

	def __eq__(self, other):
		try:
			return self is other or self.id == other.id
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.id)
		return xhash

	def __str__(self):
		return self.id

@interface.implementer(graph_interfaces.IContainer)
@component.adapter(basestring)
def _default_container_adapter(containerId):
	return Container(containerId)

def _has_pk(obj):
	adapted = graph_interfaces.IUniqueAttributeAdapter(obj, None)
	return adapted is not None and adapted.key and adapted.value

def _get_containerId(obj):
	containerId = getattr(obj, 'containerId', None)
	if not containerId:
		parent = getattr(obj, '__parent__', None)
		if parent is not None:
			containerId = to_external_ntiid_oid(parent)
	return containerId

def _update_container(db, container=None, containerId=None):
	if container is None:
		container = ntiids.find_object_with_ntiid(containerId)
	container = container or graph_interfaces.IContainer(containerId)
	if container is not None and _has_pk(container):
		adapted = graph_interfaces.IUniqueAttributeAdapter(container)
		node = db.get_indexed_node(adapted.key, adapted.value)
		if node is not None:
			properties = getattr(node, 'properties', None) or {}
			createdTime = properties.get('createdTime')
			labels = graph_interfaces.ILabelAdapter(container)
			properties = graph_interfaces.IPropertyAdapter(container)
			if createdTime is not None:
				properties['createdTime'] = createdTime
			db.update_node(node, labels, properties)
			logger.debug("properties updated for node %s", node)

def _add_contained_membership(db, oid, containerId):
	obj = ntiids.find_object_with_ntiid(oid)
	container = ntiids.find_object_with_ntiid(containerId)
	if obj is not None and _has_pk(obj):
		container = container or graph_interfaces.IContainer(containerId)
		result = db.create_relationship(obj, container, relationships.Contained())
		if result is not None:
			logger.debug("containment relationship %s retreived/created", result)
			return True
		_update_container(db, container=container)
	return False

def _process_contained_added(db, contained):
	containerId = _get_containerId(contained)
	if containerId:
		oid = to_external_ntiid_oid(contained)
		queue = get_job_queue()
		job = create_job(_add_contained_membership, db=db, oid=oid,
						 containerId=containerId)
		queue.put(job)

@component.adapter(nti_interfaces.IContained, lce_interfaces.IObjectAddedEvent)
def _contained_added(contained, event):
	db = get_graph_db()
	if db is not None:
		_process_contained_added(db, contained)

def _process_contained_modified(db, contained):
	containerId = _get_containerId(contained)
	if containerId:
		queue = get_job_queue()
		job = create_job(_update_container, db=db, containerId=containerId)
		queue.put(job)

@component.adapter(nti_interfaces.IContained, lce_interfaces.IObjectModifiedEvent)
def _contained_modified(contained, event):
	db = get_graph_db()
	if db is not None:
		_process_contained_modified(db, contained)

def _remove_node(db, key, value):
	node = db.get_indexed_node(key, value)
	if node is not None:
		db.delete_node(node)
		logger.debug("node %s deleted", node)
		return True
	return False

def _process_contained_removed(db, contained):
	adapted = graph_interfaces.IUniqueAttributeAdapter(contained)
	queue = get_job_queue()
	job = create_job(_remove_node, db=db, key=adapted.key, value=adapted.value)
	queue.put(job)
	_process_contained_modified(db, contained)  # update parent

@component.adapter(nti_interfaces.IContained, intid_interfaces.IIntIdRemovedEvent)
def _contained_removed(contained, event):
	db = get_graph_db()
	if db is not None:
		_process_contained_removed(db, contained)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if nti_interfaces.IContained.providedBy(obj):
		_process_contained_added(db, obj)
		result = True
	return result
