#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.threadlocal import get_current_request

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids

from .common import to_external_ntiid_oid

from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import relationships
from . import interfaces as graph_interfaces

def get_current_user():
	request = get_current_request()
	username = request.authenticated_userid if request is not None else None
	return username

def add_flagged_relationship(db, username, oid):
	result = None
	author = users.User.get_user(username)
	obj = ntiids.find_object_with_ntiid(oid)
	if obj is not None and author is not None:
		rel_type = relationships.Flagged()
		result = db.create_relationship(author, obj, rel_type)
		logger.debug("%s relationship %s created", rel_type, result)
	return result

def remove_flagged_relationship(db, username, oid):
	result = False
	author = users.User.get_user(username)
	obj = ntiids.find_object_with_ntiid(oid)
	if obj is not None and author is not None:
		rel_type = relationships.Flagged()
		match = db.match(author, obj, rel_type)
		if match and db.delete_relationships(match[0]):
			logger.debug("%s relationship %s deleted", rel_type, match[0])
			result = True
	return result

def _process_flagging_event(db, flaggable, username=None, is_flagged=True):
	username = username or get_current_user()
	if username:
		oid = to_external_ntiid_oid(flaggable)
		queue = get_job_queue()
		if is_flagged:
			job = create_job(add_flagged_relationship, db=db, username=username,
							 oid=oid)
		else:
			job = create_job(remove_flagged_relationship, db=db, username=username,
							 oid=oid)
		queue.put(job)

@component.adapter(nti_interfaces.IFlaggable, nti_interfaces.IObjectFlaggedEvent)
def _object_flagged(flaggable, event):
	db = get_graph_db()
	if db is not None:
		_process_flagging_event(db, flaggable)

@component.adapter(nti_interfaces.IFlaggable, nti_interfaces.ObjectUnflaggedEvent)
def _object_unflagged(flaggable, event):
	db = get_graph_db()
	if db is not None:
		_process_flagging_event(db, flaggable, is_flagged=False)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if nti_interfaces.IFlaggable.providedBy(obj):
		store = nti_interfaces.IGlobalFlagStorage(obj)
		if store.is_flagged(obj):
			creator = getattr(obj, 'creator', None)
			# asume all sharedWith users have flagged object
			flaggers = list(getattr(obj, 'sharedWith', ()))
			if not flaggers and creator:
				flaggers.append(creator)
			flaggers = {getattr(x,'username', x) for x in flaggers}
			for flagger in flaggers:
				_process_flagging_event(db, obj, flagger)
			result = len(flaggers) > 0
	return result
