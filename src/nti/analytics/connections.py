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

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

from datetime import datetime

from nti.ntiids import ntiids

from .common import to_external_ntiid_oid

from . import create_job
from . import get_analytics_db
from . import get_job_queue
from . import interfaces as analytics_interfaces

def _update_connections(db, entity, graph_relations_func, db_relations_func, rel_type):
	# computer db/graph relationships
	entity = get_entity(entity)
	stored_db_relations = db_relations_func(entity)
	current_graph_relations = graph_relations_func(db, entity)
	to_add = stored_db_relations - current_graph_relations
	to_remove = current_graph_relations - stored_db_relations

	# remove old relationships
	if to_remove:
		db.delete_relationships(*[x.rel for x in to_remove])
		logger.debug("%s connection relationship(s) deleted", len(to_remove))

	# create nodes
	to_create = set()
	for fship in to_add:
		to_create.add(fship._to)
		to_create.add(fship._from)
	if to_create:
		to_create = list(to_create)
		db.create_nodes(*to_create)

	# add new relationships
	result = []
	for fship in to_add:
		_to = fship._to
		_from = fship._from
		rel = db.create_relationship(_from, _to, rel_type)
		logger.debug("connection relationship %s created", rel)
		result.append(rel)
	return result

# friendship

def db_friends(entity):
	result = set()
	friendlists = getattr(entity, 'friendsLists', {}).values()
	for fnd_list in friendlists:
		for friend in fnd_list:
			result.add(_Relationship(entity, friend))
	return result

def update_friendships(db, entity):
	result = _update_connections(db, entity,
								 graph_friends,
								 db_friends,
								 relationships.FriendOf())
	return result

def _process_friendslist_event(db, obj):
	if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(obj):
		return # pragma no cover

	username = getattr(obj.creator, 'username', obj.creator)
	queue = get_job_queue()
	job = create_job(update_friendships, db=db, entity=username)
	queue.put(job)

def _process_friends_list_created(db, obj):
	if nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(obj):
		return # pragma no cover

	username = getattr(obj.creator, 'username', obj.creator)
	queue = get_job_queue()
	job = create_job(update_friendships, db=db, entity=username)
	queue.put(job)
 
@component.adapter(nti_interfaces.IFriendsList, lce_interfaces.IObjectAddedEvent)
def _friendslist_added(obj, event):
	db = get_analytics_db()
	if db is not None:
		_process_friendslist_event(db, obj)

@component.adapter(nti_interfaces.IFriendsList, lce_interfaces.IObjectModifiedEvent)
def _friendslist_modified(obj, event):
	db = get_analytics_db()
	if db is not None:
		_process_friendslist_event(db, obj)

@component.adapter(nti_interfaces.IFriendsList, intid_interfaces.IIntIdRemovedEvent)
def _friendslist_deleted(obj, event):
	db = get_analytics_db()
	if db is not None:
		_process_friendslist_event(db, obj)

def update_memberships(db, entity):
	result = _update_connections(db, entity,
								 graph_memberships,
								 db_memberships,
								 relationships.MemberOf())
	return result

def process_start_membership(db, source, target):
	source = users.Entity.get_entity(source)
	target = ntiids.find_object_with_ntiid(target)
	if source and target:
		session = db.get_session()
		nti_session = None
		timestamp = None
		rel = db.create_dynamic_friends_member( session, nti_session, source, timestamp, target, source )
		session.commit()
		logger.debug("DFL joined by (%s)", rel)

def process_stop_membership(db, source, target):
	source = users.Entity.get_entity(source)
	target = ntiids.find_object_with_ntiid(target)
	if source and target:
		session = db.get_session()
		nti_session = None
		timestamp = None
		rel = db.remove_dynamic_friends_member( session, nti_session, source, timestamp, target, source )
		session.commit()
		logger.debug("DFL left by (%s)", rel)

def _process_membership_event(db, event):
	source, target = event.object, event.target
	everyone = users.Entity.get_entity('Everyone')
	if target == everyone:
		return # pragma no cover

	source = source.username
	target = to_external_ntiid_oid(target)
	start_membership = nti_interfaces.IStartDynamicMembershipEvent.providedBy(event)

	queue = get_job_queue()
	if start_membership:
		job = create_job(process_start_membership, db=db, source=source, target=target)
	else:
		job = create_job(process_stop_membership, db=db, source=source, target=target)
	queue.put(job)

@component.adapter(nti_interfaces.IStartDynamicMembershipEvent)
def _start_dynamic_membership_event(event):
	db = get_analytics_db()
	if db is not None:
		_process_membership_event(db, event)

@component.adapter(nti_interfaces.IStopDynamicMembershipEvent)
def _stop_dynamic_membership_event(event):
	db = get_analytics_db()
	if db is not None:
		_process_membership_event(db, event)

def _do_membership_deletions(db, keyref):
	queue = get_job_queue()
	job = create_job(_delete_index_relationship, db=db, keyref=keyref)
	queue.put(job)

def _process_deleted_dfl( db, dfl, timestamp ):
	session = db.get_session()
	nti_session = None
	db.remove_dynamic_friends_list( session, user, nti_session, timestamp, dfl )
	session.commit()

@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList,
				   intid_interfaces.IIntIdRemovedEvent)
def _dfl_deleted(obj, event):
	# FIXME why persist db?
	# FIXME where is dfl added event?
	# FIXME user
	# TODO how about dfl intid? Or is this a string entity?
	db = get_analytics_db()
	queue = get_job_queue()
	job = create_job( 	_process_deleted_dfl, 
						db=db, dfl=obj, 
						timestamp=datetime.utcnow() )
	queue.put(job)
	

# Contacts

def process_follow(db, source, followed):
	source = users.Entity.get_entity(source)
	followed = users.Entity.get_entity(followed)
	if source and followed:
		session = db.get_session()
		nti_session = None
		timestamp = None
		db.create_contact_added( session, source, nti_session, timestamp, followed )
		session.commit()
		logger.debug("Contact added (%s->%s)", source, followed)
	return None

def process_unfollow(db, source, followed):
	source = users.Entity.get_entity(source)
	followed = users.Entity.get_entity(followed)
	if source and followed:
		session = db.get_session()
		nti_session = None
		timestamp = None
		db.create_contact_removed( session, source, nti_session, timestamp, followed )
		session.commit()
		logger.debug("Contact removed (%s->%s)", source, followed)
	return None

def _process_follow_event(db, event):
	source = getattr(event.object, 'username', event.object)
	stop_following = nti_interfaces.IStopFollowingEvent.providedBy(event)
	followed = event.not_following if stop_following else event.now_following
	followed = getattr(followed, 'username', followed)
	
	queue = get_job_queue()
	if stop_following:
		job = create_job(process_unfollow, db=db, source=source, followed=followed)
	else:
		job = create_job(process_follow, db=db, source=source, followed=followed)
	queue.put(job)

@component.adapter(nti_interfaces.IEntityFollowingEvent)
def _start_following_event(event):
	db = get_analytics_db()
	if db is not None:
		_process_follow_event(db, event)

@component.adapter(nti_interfaces.IStopFollowingEvent)
def _stop_following_event(event):
	db = get_analytics_db()
	if db is not None:
		_process_follow_event(db, event)

# Contact
def _process_following(db, user):
	source = user.username
	queue = get_job_queue()
	for followed in getattr(user, 'entities_followed', ()):
		followed = getattr(followed, 'username', followed)
		job = create_job(process_follow, db=db, source=source, followed=followed)
		queue.put(job)

def _process_memberships(db, user):
	source = user.username
	queue = get_job_queue()
	everyone = users.Entity.get_entity('Everyone')
	for target in getattr(user, 'dynamic_memberships', ()):
		if target != everyone:
			target = to_external_ntiid_oid(target)
			job = create_job(	process_start_membership, db=db, 
								source=source,
								target=target)
			queue.put(job)

def _process_friendships(db, user):
	queue = get_job_queue()
	job = create_job(update_friendships, db=db, entity=user.username)
	queue.put(job)

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init(db, obj):
	result = False
	if nti_interfaces.IUser.providedBy(obj):
		_process_following(db, obj)
		_process_memberships(db, obj)
		_process_friendships(db, obj)
		result = True
	return result
