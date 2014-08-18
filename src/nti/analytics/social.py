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

from datetime import datetime

from nti.chatserver import interfaces as chat_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.ntiids import ntiids

from nti.intid import interfaces as intid_interfaces

from nti.analytics import interfaces as analytic_interfaces

from .common import get_creator
from .common import get_nti_session_id
from .common import process_event
from .common import get_created_timestamp
from .common import get_entity

from nti.analytics.database import social as db_social

from nti.analytics.identifier import FriendsListId
from nti.analytics.identifier import DFLId
_dflid = DFLId()
_flid = FriendsListId()

from nti.analytics import get_factory
from nti.analytics import SOCIAL_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SOCIAL_ANALYTICS )

def _is_friends_list( obj ):
	return 	nti_interfaces.IFriendsList.providedBy( obj ) \
		and not nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ) \
		and not _is_contacts_friends_list( obj )

def _is_contacts_friends_list( obj ):
	# Look for 'mycontacts'; is there a better way to do this?
	return 	nti_interfaces.IFriendsList.providedBy( obj ) \
		and 'mycontacts' in obj.__name__

# Chat
def _add_meeting( oid, nti_session=None ):
	new_chat = ntiids.find_object_with_ntiid(oid)
	if new_chat is not None:
		creator = get_creator( new_chat )
		db_social.create_chat_initiated( creator, nti_session, new_chat )
		logger.debug( "Meeting created (user=%s) (meeting=%s)", creator, new_chat )

		timestamp = get_created_timestamp( new_chat )
		users_joined = getattr( new_chat, 'historical_occupant_names', ())
		count = 0
		for user_joined in users_joined:
			count += 1
			user_joined = get_entity( user_joined )
			if user_joined is not None:
				db_social.chat_joined( user_joined, nti_session, timestamp, new_chat )
		logger.debug( "Meeting joined by users (count=%s)", count )

def _update_meeting( oid, timestamp=None ):
	chat = ntiids.find_object_with_ntiid(oid)
	if chat is not None:
		current_members = getattr( chat, 'historical_occupant_names', ())
		new_members = (get_entity(x) for x in current_members)
		count = db_social.update_chat( timestamp, chat, new_members )
		logger.debug( "Meeting joined by new users (count=%s)", count )

@component.adapter(chat_interfaces.IMeeting, intid_interfaces.IIntIdAddedEvent)
def _meeting_created(meeting, event):
	creator = get_creator( meeting )
	nti_session = get_nti_session_id( creator )
	process_event( _get_job_queue, _add_meeting, meeting, nti_session=nti_session )

@component.adapter( chat_interfaces.IMeeting, lce_interfaces.IObjectModifiedEvent )
def _meeting_joined( meeting, event ):
	timestamp = datetime.utcnow()
	process_event( _get_job_queue, _update_meeting, meeting, timestamp=timestamp )

# Contacts
def _add_contacts( oid, timestamp=None, nti_session=None ):
	""" Intended, during migration, to add all of a user's contacts. """
	user = ntiids.find_object_with_ntiid(oid)
	if user is not None:
		user = get_entity( user )
		entities_followed = getattr(user, 'entities_followed', ())

		# Only add users (not Communities)
		entities_followed = (get_entity( x )
							for x in entities_followed
							if nti_interfaces.IUser.providedBy( x ) )
		count = db_social.update_contacts( user, nti_session, timestamp, entities_followed )
		logger.debug( "Contacts added (user=%s) (count=%s)", user, count )

# Friends List
def _add_friends_list( oid, nti_session=None ):
	friends_list = ntiids.find_object_with_ntiid(oid)
	if friends_list is not None:
		user = get_creator( friends_list )
		timestamp = get_created_timestamp( friends_list )
		db_social.create_friends_list( user, nti_session, timestamp, friends_list )
		logger.debug( 	"FriendsList created (user=%s) (friends_list=%s) (count=%s)",
						user,
						friends_list,
						len( friends_list ) )

def _remove_friends_list(friends_list_id, timestamp=None):
	db_social.remove_friends_list( timestamp, friends_list_id )
	logger.debug( "FriendsList removed (friends_list=%s)", friends_list_id )

def _update_friends_list( oid, nti_session=None, timestamp=None ):
	friends_list = ntiids.find_object_with_ntiid( oid )
	if friends_list is not None:
		# Creator makes sense for contacts, but what about friends_list?
		user = get_creator( friends_list )
		# We end up comparing membership lists. Expensive?
		if _is_contacts_friends_list( friends_list ):
			result = db_social.update_contacts( user, nti_session, timestamp, friends_list )
			logger.debug( 'Update contacts (user=%s) (count=%s)', user, result )
		else:
			result = db_social.update_friends_list( user, nti_session, timestamp, friends_list )
			logger.debug( 'Update FriendsList (user=%s) (count=%s)', user, result )

@component.adapter(nti_interfaces.IFriendsList, intid_interfaces.IIntIdAddedEvent)
def _friendslist_added(obj, event):
	if _is_friends_list( obj ):
		user = get_creator( obj )
		nti_session = get_nti_session_id( user )
		process_event( _get_job_queue, _add_friends_list, obj, nti_session=nti_session )

@component.adapter(nti_interfaces.IFriendsList, lce_interfaces.IObjectModifiedEvent)
def _friendslist_modified(obj, event):
	if not nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		timestamp = datetime.utcnow()
		user = get_creator( obj )
		nti_session = get_nti_session_id( user )
		process_event( _get_job_queue, _update_friends_list, obj, nti_session=nti_session, timestamp=timestamp )

@component.adapter(nti_interfaces.IFriendsList, intid_interfaces.IIntIdRemovedEvent)
def _friendslist_deleted(obj, event):
	if _is_friends_list( obj ):
		id = _flid.get_id( obj )
		timestamp = datetime.utcnow()
		process_event( _get_job_queue, _remove_friends_list, friends_list_id=id, timestamp=timestamp )


# DFL
def _add_dfl( oid, nti_session=None ):
	dfl = ntiids.find_object_with_ntiid(oid)
	if dfl is not None:
		user = get_creator( dfl )
		db_social.create_dynamic_friends_list( user, nti_session, dfl )
		for member in dfl:
			member = get_entity( member )
			if member is not None:
				db_social.create_dynamic_friends_member( user, nti_session, None, dfl, member )
		logger.debug( "DFL created (user=%s) (dfl=%s) (count=%s)", user, dfl, len( dfl ) )

def _remove_dfl( dfl_id, timestamp=None ):
	db_social.remove_dynamic_friends_list( timestamp, dfl_id )
	logger.debug( "DFL destroyed (dfl=%s)", dfl_id )

def _add_dfl_member( source, target, username=None, timestamp=None, nti_session=None ):
	dfl = get_entity( target )
	member = get_entity( source )
	everyone = users.Entity.get_entity('Everyone')

	if 		dfl is not None \
		and member is not None \
		and dfl != everyone:
		user = get_entity( username )
		db_social.create_dynamic_friends_member( user, nti_session, timestamp, dfl, member )
		logger.debug( "DFL joined (member=%s) (dfl=%s)", member, dfl )

def _remove_dfl_member( source, target, username=None, timestamp=None, nti_session=None ):
	dfl = get_entity( target )
	if dfl is not None:
		user = get_entity( username )
		member = get_entity( source )
		db_social.remove_dynamic_friends_member( user, nti_session, timestamp, dfl, member )
		logger.debug( "DFL left (member=%s) (dfl=%s)", member, dfl )

@component.adapter(	nti_interfaces.IDynamicSharingTargetFriendsList,
				 	 intid_interfaces.IIntIdAddedEvent)
def _dfl_added(obj, event):
	user = get_creator( obj )
	nti_session = get_nti_session_id( user )
	process_event( _get_job_queue, _add_dfl, obj, nti_session=nti_session )

@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList,
				  intid_interfaces.IIntIdRemovedEvent)
def _dfl_deleted(obj, event):
	timestamp = datetime.utcnow()
	id = _dflid.get_id( obj )
	process_event( _get_job_queue, _remove_dfl, dfl_id=id, timestamp=timestamp )

def _handle_dfl_membership_event( event, to_call ):
	timestamp = datetime.utcnow()
	source = getattr(event.object, 'username', event.object)
	target = event.target
	# We ignore Community events (enrollments)
	if nti_interfaces.ICommunity.providedBy( target ):
		return

	target = getattr(target, 'username', target)

	nti_session = get_nti_session_id( get_entity( source ) )
	process_event( _get_job_queue,
					to_call,
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
		process_event( _get_job_queue, _add_meeting, obj )
	elif nti_interfaces.IDynamicSharingTargetFriendsList.providedBy( obj ):
		process_event( _get_job_queue, _add_dfl, obj )
	elif _is_friends_list( obj ):
		process_event( _get_job_queue, _add_friends_list, obj )
	elif nti_interfaces.IUser.providedBy(obj):
		process_event( _get_job_queue, _add_contacts, obj )
	else:
		result = False
	return result
