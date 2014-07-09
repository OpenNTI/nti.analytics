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

from nti.chatserver import interfaces as chat_interfaces
from nti.chatserver.meeting import EVT_ENTERED_ROOM
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.ntiids import ntiids

from nti.intid import interfaces as intid_interfaces

from datetime import datetime

from .common import to_external_ntiid_oid

from .common import get_creator
from .common import get_nti_session_id
from .common import get_deleted_time
from .common import get_comment_root
from .common import get_course
from .common import process_event
from .common import get_created_timestamp
from .common import get_entity
from .common import IDLookup

from . import utils
from . import interfaces as analytic_interfaces

# Chat
def _add_meeting(db, oid, nti_session=None ):
	new_chat = ntiids.find_object_with_ntiid(oid)
	if new_chat is not None:
		# Idempotent if we also have participant joining events
		creator = get_creator( new_chat )
		db.create_chat_initiated( session, creator, nti_session, new_chat )
		logger.debug( "Meeting created (user=%s) (meeting=%s)", creator, new_chat )
		
		timestamp = get_created_timestamp( new_chat )
		users_joined = getattr( obj , 'historical_occupant_names', ())
		count = 0
		for user_joined in users_joined:
			count += 1
			user_joined = get_entity( user_joined )
			db.chat_joined( user_joined, nti_session, timestamp, new_chat )
		logger.debug( "Meeting joined by users (count=%s)", count )

def _join_meeting( db, oid, timestamp=None, nti_session=None ):
	chat = ntiids.find_object_with_ntiid(oid)
	if chat is not None:
		# FIXME implement
		# user-joined?
		db.create_chat_joined( session, user_joined, nti_session, timestamp, chat)

@component.adapter(chat_interfaces.IMeeting, intid_interfaces.IIntIdAddedEvent)
def _meeting_created(meeting, event):
	creator = get_creator( meeting )
	nti_session = get_nti_session_id( creator )
	process_event( _add_meeting, meeting, nti_session=nti_session )

@component.adapter( chat_interfaces.IMeeting, lce_interfaces.IObjectModifiedEvent )
def _meeting_joined( meeting, event ):
	# TODO Verify/implement this...
	# TODO nti_session
	#from IPython.core.debugger import Tracer;Tracer()()
	timestamp = datetime.utcnow()
	process_event( _join_meeting, meeting, timestamp=timestamp )

# Contacts	
def _add_contacts( db, oid, timestamp=None, nti_session=None ):
	user = ntiids.find_object_with_ntiid(oid)
	if user is not None:
		user = get_entity( user )
		entities_followed = getattr(user, 'entities_followed', ())
		count = 0
		for followed in entities_followed:
			# Only add users (have seen Communities here)
			if not nti_interfaces.IUser.providedBy( followed ):
				continue
			count += 1
			followed = get_entity( followed )
			db.create_contact_added( user, nti_session, timestamp, followed )
		logger.debug( "Contacts added (user=%s) (count=%s)", user, count )

def _add_contact( db, source, target, timestamp=None, nti_session=None ):
	source = get_entity( source )
	target = get_entity( target )
	db.create_contact_added( source, nti_session, timestamp, target )
	logger.debug( "Contact added (user=%s) (target=%s)", source, target )

def _remove_contact( db, source, target, timestamp=None, nti_session=None ):
	source = get_entity( source )
	target = get_entity( target )
	db.contact_removed( source, nti_session, timestamp, target )
	logger.debug( "Contact removed (user=%s) (target=%s)", source, target )

@component.adapter(nti_interfaces.IEntityFollowingEvent)
def _start_following_event(event):
	if		nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( event.now_following ) \
		or 	nti_interfaces.ICommunity.providedBy( event.now_following ):
		return
	timestamp = datetime.utcnow()
	source = getattr( event.object, 'username', event.object )
	followed = event.now_following
	followed = getattr( followed, 'username', followed )
	
	nti_session = get_nti_session_id( get_entity( source ) )
	process_event( _add_contact, source=source, target=followed, timestamp=timestamp, nti_session=nti_session )

@component.adapter(nti_interfaces.IStopFollowingEvent)
def _stop_following_event(event):
	if		nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( event.not_following ) \
		or 	nti_interfaces.ICommunity.providedBy( event.not_following ):
		return
	timestamp = datetime.utcnow()
	source = getattr(event.object, 'username', event.object)
	followed = event.not_following
	followed = getattr(followed, 'username', followed)
	nti_session = get_nti_session_id( get_entity( source ) )
	process_event( _remove_contact, source=source, target=followed, timestamp=timestamp, nti_session=nti_session )

# Friends List
def _add_friends_list( db, oid, nti_session=None ):
	friends_list = ntiids.find_object_with_ntiid(oid)
	if friends_list is not None:
		user = get_creator( friends_list )
		timestamp = get_created_timestamp( friends_list )
		db.create_friends_list( user, nti_session, timestamp, friends_list )
		for member in friends_list:
			member = get_entity( member )
			db.create_friends_list_member( user, nti_session, None, friends_list, member )
		logger.debug( 	"FriendsList created (user=%s) (friends_list=%s) (count=%s", 
						user, 
						friends_list,
						len( friends_list ) )		

def _remove_friends_list(db, friends_list_id, timestamp=None):
	db.remove_friends_list( timestamp, friends_list_id )
	logger.debug( "FriendsList removed (friends_list=%s)", friends_list )


def _modified_friends_list( db, oid, timestamp=None ):
	friends_list = ntiids.find_object_with_ntiid( oid )
	if friends_list is not None:
		pass
		#FIXME implement
		# What is the best we can do here, compare memberships?
		# Expensive?

@component.adapter(nti_interfaces.IFriendsList, intid_interfaces.IIntIdAddedEvent)
def _friendslist_added(obj, event):
	if not nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		user = get_creator( obj )
		nti_session = get_nti_session_id( user )
		process_event( _add_friends_list, obj, nti_session=nti_session )

@component.adapter(nti_interfaces.IFriendsList, lce_interfaces.IObjectModifiedEvent)
def _friendslist_modified(obj, event):
	if not nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		# Should be joins/removals
		timestamp = datetime.utcnow()
		process_event( _modified_friends_list, obj, timestamp=timestamp )

@component.adapter(nti_interfaces.IFriendsList, intid_interfaces.IIntIdRemovedEvent)
def _friendslist_deleted(obj, event):
	if not nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		id_lookup = IDLookup()
		id = id_lookup.get_id_for_object( obj )
		timestamp = datetime.utcnow()
		process_event( _remove_friends_list, friends_list_id=id, timestamp=timestamp )


# DFL
def _add_dfl( db, oid, nti_session=None ):
	dfl = ntiids.find_object_with_ntiid(oid)
	if dfl is not None:
		user = get_creator( dfl )
		db.create_dynamic_friends_list( user, nti_session, dfl )
		for member in dfl:
			member = get_entity( member )
			db.create_dynamic_friends_member( user, nti_session, None, dfl, member )
		logger.debug( "DFL created (user=%s) (dfl=%s) (count=%s)", user, dfl, len( dfl ) )		

def _remove_dfl( db, dfl_id, timestamp=None ):
	db.remove_dynamic_friends_list( timestamp, dfl_id )
	logger.debug( "DFL destroyed (dfl=%s)", dfl )

def _add_dfl_member( db, source, target, username=None, timestamp=None, nti_session=None ):
	dfl = get_entity( target )
	member = get_entity( source )
	everyone = users.Entity.get_entity('Everyone')
	
	if 		dfl is not None \
		and member is not None \
		and dfl != everyone:
		user = get_entity( username )
		db.create_dynamic_friends_member( user, nti_session, timestamp, dfl, member )
		logger.debug( "DFL joined (member=%s) (dfl=%s)", member, dfl )		

def _remove_dfl_member( db, source, target, username=None, timestamp=None, nti_session=None ):
	dfl = get_entity( target )
	if dfl is not None:
		user = get_entity( username )
		member = get_entity( source )
		db.remove_dynamic_friends_member( user, nti_session, timestamp, dfl, member )
		logger.debug( "DFL left (member=%s) (dfl=%s)", member, dfl )

@component.adapter(	nti_interfaces.IDynamicSharingTargetFriendsList,
				 	 intid_interfaces.IIntIdAddedEvent)
def _dfl_added(obj, event):
	user = get_creator( obj )
	nti_session = get_nti_session_id( user )
	process_event( _add_dfl, obj, nti_session=nti_session )
	
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList,
				  intid_interfaces.IIntIdRemovedEvent)
def _dfl_deleted(obj, event):	
	timestamp = datetime.utcnow()
	id_lookup = IDLookup()
	id = id_lookup.get_id_for_object( obj )
	process_event( _remove_dfl, dfl_id=id, timestamp=timestamp )

def _handle_dfl_membership_event( event, to_call ):
	timestamp = datetime.utcnow()
	source = getattr(event.object, 'username', event.object)
	target = event.target
	# We ignore Community events (enrollments)
	if nti_interfaces.ICommunity.providedBy( target ):
		return
	
	target = getattr(target, 'username', target)
	
	nti_session = get_nti_session_id( get_entity( source ) )
	process_event( 	to_call, 
					source=source,
					target=target, 
					timestamp=timestamp, 
					nti_session=nti_session )

@component.adapter(nti_interfaces.IStartDynamicMembershipEvent)
def _start_dynamic_membership_event(event):
	_handle_dfl_membership_event( event, _add_dfl_member )

@component.adapter(nti_interfaces.IStopDynamicMembershipEvent)
def _stop_dynamic_membership_event(event):
	_handle_dfl_membership_event( event, _remove_dfl_member )


component.moduleProvides(analytic_interfaces.IObjectProcessor)
def init( obj ):
	result = True
	if chat_interfaces.IMeeting.providedBy(obj):
		process_event( _add_meeting, obj )
	elif nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		process_event( _add_dfl, obj )
		
	# Exclude 'mycontacts', better way to do this?	
	elif 	nti_interfaces.IFriendsList.providedBy( obj ) \
		and 'mycontacts' not in obj.__name__:
		
		process_event( _add_friends_list, obj )
	elif nti_interfaces.IUser.providedBy(obj):
		
		process_event( _add_contacts, obj )
	else:
		result = False
	return result
