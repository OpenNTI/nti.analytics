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
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.ntiids import ntiids

from .common import to_external_ntiid_oid

from .common import get_creator
from .common import get_nti_session
from .common import get_deleted_time
from .common import get_comment_root
from .common import get_course
from .common import process_event
from .common import get_created_timestamp
from .common import get_entity

from . import utils
from . import interfaces as analytic_interfaces

# Chat
def _add_meeting(db, oid):
	new_chat = ntiids.find_object_with_ntiid(oid)
	if new_chat is not None:
		# FIXME need session
		# Idempotent if we also have participant joining events
		creator = get_creator( new_chat )
		nti_session = None
		db.chat_initiated( session, creator, nti_session, new_chat )
		logger.debug( "Meeting created (user=%s) (meeting=%s)", creator, new_chat )
		
		timestamp = get_created_timestamp( new_chat )
		users_joined = getattr( obj , 'historical_occupant_names', ())
		count = 0
		for user_joined in users_joined:
			count += 1
			user_joined = get_entity( user_joined )
			db.chat_joined( user_joined, nti_session, timestamp, new_chat )
		logger.debug( "Meeting joined by users (count=%s)", count )

# def _join_meeting(db, user, oid):
# 	chat = ntiids.find_object_with_ntiid(oid)
# 	if chat is not None:
# 		# FIXME timestamp, session
# 		nti_session = None
# 		join_timestamp = None
# 		user_joined = get_entity(user)
# 		db.create_chat_joined( session, user_joined, nti_session, join_timestamp, chat)

@component.adapter(chat_interfaces.IMeeting, lce_interfaces.IObjectAddedEvent)
def _meeting_created(meeting, event):
	# FIXME We need event for participants, IObjectModifiedEvent?
	# self.emit_enteredRoom( name, self )
	process_event( _add_meeting, meeting )

# Contacts	
def _add_contacts( db, oid, timestamp=None ):
	user = ntiids.find_object_with_ntiid(oid)
	if user is not None:
		user = get_entity( user )
		# FIXME need session
		nti_session = None
		entities_followed = getattr(user, 'entities_followed', ())
		count = 0
		for followed in entities_followed:
			count += 1
			followed = get_entity( followed )
			db.create_contact_added( user, nti_session, timestamp, followed )
		logger.debug( "Contacts added (user=%s) (count=%s)", user, count )

def _add_contact( db, source, target, timestamp=None ):
	source = get_entity( source )
	target = get_entity( target )
	nti_session = None
	db.create_contact_added( source, nti_session, timestamp, target )
	logger.debug( "Contact added (user=%s) (target=%s)", source, target )

def _remove_contact( db, source, target, timestamp=None ):
	source = get_entity( source )
	target = get_entity( target )
	nti_session = None
	db.contact_removed( source, nti_session, timestamp, target )
	logger.debug( "Contact removed (user=%s) (target=%s)", source, target )

@component.adapter(nti_interfaces.IEntityFollowingEvent)
def _start_following_event(event):
	from IPython.core.debugger import Tracer;Tracer()()
	# TODO timestamp
	source = getattr( event.object, 'username', event.object )
	followed = event.now_following
	followed = getattr( followed, 'username', followed )
	process_event( _add_contact, source=source, target=followed )

@component.adapter(nti_interfaces.IStopFollowingEvent)
def _stop_following_event(event):
	source = getattr(event.object, 'username', event.object)
	followed = event.not_following
	followed = getattr(followed, 'username', followed)
	process_event( _remove_contact, source=source, target=followed )

# Friends List
def _add_friends_list(db, oid):
	friends_list = ntiids.find_object_with_ntiid(oid)
	if friends_list is not None:
		# FIXME need session
		nti_session = None
		user = get_creator( friends_list )
		timestamp = get_created_timestamp( friends_list )
		db.create_friends_list( user, nti_session, timestamp, friends_list )
		# FIXME add members
		logger.debug( "FriendsList created (user=%s) (friends_list=%s)", user, friends_list )		

def _remove_friends_list(db, oid, timestamp=None):
	# TODO For removal events like this, will these objects exist?
	# This also comes up a lot.
	friends_list = ntiids.find_object_with_ntiid(oid)
	if friends_list is not None:
		db.remove_friends_list( timestamp, friends_list )
		logger.debug( "FriendsList removed (friends_list=%s)", friends_list )


def _modified_friends_list( db, oid, timestamp=None ):
	friends_list = ntiids.find_object_with_ntiid( oid )
	if friends_list is not None:
		pass
		#FIXME implement
		# What is the best we can do here, compare memberships?
		# Expensive?

@component.adapter(nti_interfaces.IFriendsList, lce_interfaces.IObjectAddedEvent)
def _friendslist_added(obj, event):
	process_event( _add_friends_list, obj )

@component.adapter(nti_interfaces.IFriendsList, lce_interfaces.IObjectModifiedEvent)
def _friendslist_modified(obj, event):
	# Should be joins/removals
	process_event( _modified_friends_list, obj )

@component.adapter(nti_interfaces.IFriendsList, intid_interfaces.IIntIdRemovedEvent)
def _friendslist_deleted(obj, event):
	process_event( _remove_friends_list, obj )


# DFL
# TODO events for creating DFLs?
def _add_dfl( db, oid ):
	dfl = ntiids.find_object_with_ntiid(oid)
	if dfl is not None:
		# FIXME need session
		nti_session = None
		user = get_creator( dfl )
		db.create_dynamic_friends_list( user, nti_session, dfl )
		# FIXME add members
		logger.debug( "DFL created (user=%s) (dfl=%s)", user, dfl )		

def _remove_dfl( db, oid, timestamp=None ):
	# TODO For removal events like this, will these objects exist?
	dfl = ntiids.find_object_with_ntiid(oid)
	if dfl is not None:
		db.remove_friends_list( timestamp, dfl )
		logger.debug( "DFL destroyed (dfl=%s)", dfl )

def _add_dfl_member( db, source, target, username=None, timestamp=None ):
	dfl = get_entity( target )
	if dfl is not None:
		# FIXME need session
		nti_session = None
		user = get_entity( username )
		member = get_entity( source )
		db.create_dynamic_friends_member( user, nti_session, timestamp, dfl, member )
		logger.debug( "DFL joined (member=%s) (dfl=%s)", member, dfl )		

def _remove_dfl_member( db, source, target, username=None, timestamp=None ):
	dfl = get_entity( target )
	if dfl is not None:
		# FIXME need session
		nti_session = None
		user = get_entity( username )
		member = get_entity( source )
		db.remove_dynamic_friends_member( user, nti_session, timestamp, dfl, member )
		logger.debug( "DFL left (member=%s) (dfl=%s)", member, dfl )

@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList,
				   lce_interfaces.IObjectAddedEvent)
def _dfl_added(obj, event):
	process_event( _add_dfl, obj)
	
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList,
				  lce_interfaces.IObjectAddedEvent)
def _dfl_deleted(obj, event):	
	process_event( _remove_dfl, obj)

@component.adapter(nti_interfaces.IStartDynamicMembershipEvent)
def _start_dynamic_membership_event(event):
	# TODO Will DFL's have username, or do we need oid?
	source = getattr(event.object, 'username', event.object)
	target = event.target
	target = getattr(target, 'username', target)
	process_event( _add_dfl_member, source=source, target=target )

@component.adapter(nti_interfaces.IStopDynamicMembershipEvent)
def _stop_dynamic_membership_event(event):
	source = getattr(event.object, 'username', event.object)
	target = event.target
	target = getattr(target, 'username', target)
	process_event( _remove_dfl_member, source=source, target=target )


component.moduleProvides(analytic_interfaces.IObjectProcessor)
def init( obj ):
	result = True
	if chat_interfaces.IMeeting.providedBy(obj):
		from IPython.core.debugger import Tracer;Tracer()()
		process_event( _add_meeting, obj )
	elif nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		process_event( _add_dfl, obj )
	elif nti_interfaces.IFriendsList.providedBy( obj ):
		process_event( _add_friends_list, obj )
	elif nti_interfaces.IUser.providedBy(obj):
		process_event( _add_contacts, obj )
	else:
		result = False
	return result
