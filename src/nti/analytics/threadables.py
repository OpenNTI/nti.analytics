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

from .common import get_creator
from .common import to_external_ntiid_oid

from . import utils
from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import relationships
from . import interfaces as graph_interfaces

def _get_primary_key(obj):
	author = get_creator(obj)
	adapted = component.getMultiAdapter((author, obj, relationships.Reply()),
										graph_interfaces.IUniqueAttributeAdapter)
	return utils.PrimaryKey(adapted.key, adapted.value)

def _remove_node(db, key, value):
	node = db.get_indexed_node(key, value)
	if node is not None:
		db.delete_node(node)
		logger.debug("node %s deleted", node)
		return True
	return False

def _remove_threadable(db, key, value, irt_PK=None):
	if irt_PK is not None:
		rel = db.delete_indexed_relationship(irt_PK.key, irt_PK.value)
		if rel is not None:
			logger.debug("inReplyTo relationship %s deleted", rel)
	_remove_node(db, key, value)

def _proces_threadable_removed(db, threadable):
	irt_PK = _get_primary_key(threadable) if threadable.inReplyTo is not None else None
	adapted = graph_interfaces.IUniqueAttributeAdapter(threadable)
	queue = get_job_queue()
	job = create_job(_remove_threadable, db=db,
					 # threadable node locator
					 key=adapted.key,
					 value=adapted.value,
					 # inReplyTo rel locator
					 irt_PK=irt_PK)
	queue.put(job)

@component.adapter(nti_interfaces.IThreadable, intid_interfaces.IIntIdRemovedEvent)
def _threadable_removed(threadable, event):
	db = get_graph_db()
	if db is not None:
		_proces_threadable_removed(db, threadable)

@component.adapter(nti_interfaces.IThreadable, lce_interfaces.IObjectModifiedEvent)
def _threadable_modified(thread, event):
	db = get_graph_db()
	if db is not None and nti_interfaces.IDeletedObjectPlaceholder.providedBy(thread):
		_proces_threadable_removed(db, thread)

def _add_inReplyTo_relationship(db, oid):
	threadable = ntiids.find_object_with_ntiid(oid)
	in_replyTo = threadable.inReplyTo if threadable is not None else None
	if in_replyTo is not None:
		# create parent/child relationship
		rel_type = relationships.IsReplyOf()
		rel = db.create_relationship(threadable, in_replyTo, rel_type)
		logger.debug("relationship %s created", rel)

		t_author = get_creator(threadable)
		i_author = get_creator(in_replyTo)
		if not i_author or not t_author:
			return
		rel_type = relationships.Reply()

		# get the key/value to id the inReplyTo relationship
		irt_PK = _get_primary_key(threadable)

		# create a relationship between author and the author being replied to
		properties = component.getMultiAdapter((t_author, threadable, rel_type),
												graph_interfaces.IPropertyAdapter)

		result = db.create_relationship(t_author, i_author, rel_type,
										properties=properties,
										key=irt_PK.key, value=irt_PK.value)
		if result is not None:
			logger.debug("replyTo relationship %s retreived/created", result)
			return True
	return False

def _process_threadable_inReplyTo(db, threadable):
	oid = to_external_ntiid_oid(threadable)
	queue = get_job_queue()
	job = create_job(_add_inReplyTo_relationship, db=db, oid=oid)
	queue.put(job)

@component.adapter(nti_interfaces.IThreadable, lce_interfaces.IObjectAddedEvent)
def _threadable_added(threadable, event):
	db = get_graph_db()
	if db is not None and threadable.inReplyTo:
		_process_threadable_inReplyTo(db, threadable)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if nti_interfaces.IThreadable.providedBy(obj) and obj.inReplyTo:
		_process_threadable_inReplyTo(db, obj)
		result = True
	return result
