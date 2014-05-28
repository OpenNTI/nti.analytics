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
from nti.dataserver.contenttypes.forums import interfaces as forum_interfaces

from nti.ntiids import ntiids

from .common import get_entity
from .common import to_external_ntiid_oid

from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import relationships
from . import interfaces as graph_interfaces

_ENTITY_TYPES = {ntiids.TYPE_NAMED_ENTITY, ntiids.TYPE_NAMED_ENTITY.lower()}

def get_underlying(oid):
	obj = ntiids.find_object_with_ntiid(oid)
	if forum_interfaces.IHeadlinePost.providedBy(obj):
		obj = obj.__parent__
	return obj

def _create_isTaggedTo_rels(db, oid, users=()):
	obj = get_underlying(oid)
	if obj is None or not users:
		return ()

	result = []
	rel_type = relationships.TaggedTo()
	for entity in users or ():
		entity = get_entity(entity)
		if entity is not None:
			rel = db.create_relationship(obj, entity, rel_type)
			logger.debug("%s relationship %s created", rel_type, rel)
			result.append(rel)
	return result

def _process_added_event(db, obj, tags=()):
	tags = tags or getattr(obj, 'tags', ())
	username_tags = set()
	for raw_tag in tags or ():
		if ntiids.is_ntiid_of_types(raw_tag, _ENTITY_TYPES):
			entity = ntiids.find_object_with_ntiid(raw_tag)
			if entity is not None:
				username_tags.add(entity.username)

	if username_tags:
		queue = get_job_queue()
		oid = to_external_ntiid_oid(obj)
		job = create_job(_create_isTaggedTo_rels, db=db, oid=oid,
						 user_tags=list(username_tags))
		queue.put(job)

@component.adapter(nti_interfaces.IUserTaggedContent, lce_interfaces.IObjectAddedEvent)
def _user_tagged_content_added(obj, event):
	db = get_graph_db()
	if db is not None:
		_process_added_event(db, obj)

def _delete_isTaggedTo_rels(db, oid):
	obj = get_underlying(oid)
	if obj is not None:
		rel_type = relationships.TaggedTo()
		rels = db.match(start=obj, rel_type=rel_type)
		if rels:
			db.delete_relationships(*rels)
			logger.debug("isTaggedTo relationship(s) %s deleted", len(rels))
			return True
	return False

def _process_delete_rels(db, obj):
	queue = get_job_queue()
	oid = to_external_ntiid_oid(obj)
	job = create_job(_delete_isTaggedTo_rels, db=db, oid=oid)
	queue.put(job)

def _process_modified_event(db, obj):
	_process_delete_rels(db, obj)  # delete old
	_process_added_event(db, obj)  # create new

@component.adapter(nti_interfaces.IUserTaggedContent, nti_interfaces.IObjectModifiedEvent)
def _user_tagged_content_modified(obj, event):
	db = get_graph_db()
	if db is not None:
		_process_modified_event(db, obj)

def remove_user_tagged_content(db, key, value):
	node = db.get_indexed_node(key, value)
	if node is not None:
		db.delete_node(node)
		logger.debug("node %s deleted", node)
		return True
	return False

def _process_removed_event(db, obj):
	unique = graph_interfaces.IUniqueAttributeAdapter(obj)
	if unique is not None:
		key, value = unique.key, unique.value
		queue = get_job_queue()
		job = create_job(remove_user_tagged_content, db=db, key=key, value=value)
		queue.put(job)

@component.adapter(nti_interfaces.IUserTaggedContent, intid_interfaces.IIntIdRemovedEvent)
def _user_tagged_content_removed(obj, event):
	db = get_graph_db()
	if db is not None:
		_process_removed_event(db, obj)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if nti_interfaces.IUserTaggedContent.providedBy(obj):
		_process_added_event(db, obj)
		result = True
	return result
