#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey

from sqlalchemy.schema import PrimaryKeyConstraint

from sqlalchemy.ext.declarative import declared_attr

import zope.intid

from nti.dataserver.users.entity import Entity

from nti.analytics.common import get_created_timestamp
from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import ChatId
from nti.analytics.identifier import DFLId
from nti.analytics.identifier import FriendsListId
_sessionid = SessionId()
_chatid = ChatId()
_dflid = DFLId()
_flid = FriendsListId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import DeletedMixin

from nti.analytics.database.users import get_or_create_user

class DynamicFriendsListMixin(object):
	@declared_attr
	def dfl_id(cls):
		return Column('dfl_id', Integer, ForeignKey("DynamicFriendsListsCreated.dfl_id"), nullable=False, index=True )

class FriendMixin(object):
	@declared_attr
	def target_id(cls):
		return Column('target_id', Integer, ForeignKey("Users.user_id"), index=True)

class FriendsListMixin(object):
	@declared_attr
	def friends_list_id(cls):
		return Column('friends_list_id', Integer, ForeignKey("FriendsListsCreated.friends_list_id"), nullable=False, index=True )


# TODO Some of these objects do not exist in the ds, thus we'll need a sequence.  Hopefully
# we don't need any data from the ds when retrieving this data.  If so, we need it here or another
# way to look it up.

# This information needs to be obscured to protect privacy.
class ChatsInitiated(Base,BaseTableMixin):
	__tablename__ = 'ChatsInitiated'
	chat_id = Column('chat_id', Integer, nullable=False, index=True, primary_key=True, autoincrement=False )

# Note, we're not tracking when users leave chat rooms.
class ChatsJoined(Base,BaseTableMixin):
	__tablename__ = 'ChatsJoined'
	chat_id = Column('chat_id', Integer, ForeignKey("ChatsInitiated.chat_id"), nullable=False, index=True )

	__table_args__ = (
        PrimaryKeyConstraint('chat_id', 'user_id', 'timestamp'),
    )

class DynamicFriendsListsCreated(Base,BaseTableMixin,DeletedMixin):
	__tablename__ = 'DynamicFriendsListsCreated'
	dfl_id = Column('dfl_id', Integer, nullable=False, index=True, primary_key=True, autoincrement=False )

class DynamicFriendsListsMemberAdded(Base,BaseTableMixin,DynamicFriendsListMixin,FriendMixin):
	__tablename__ = 'DynamicFriendsListsMemberAdded'

	__table_args__ = (
        PrimaryKeyConstraint('dfl_id', 'target_id'),
    )

class DynamicFriendsListsMemberRemoved(Base,BaseTableMixin,DynamicFriendsListMixin,FriendMixin):
	__tablename__ = 'DynamicFriendsListsMemberRemoved'

	# Make sure we allow multiple removals
	__table_args__ = (
        PrimaryKeyConstraint('dfl_id', 'target_id', 'timestamp'),
    )

class FriendsListsCreated(Base,BaseTableMixin,DeletedMixin):
	__tablename__ = 'FriendsListsCreated'
	friends_list_id = Column('friends_list_id', Integer, nullable=False, index=True, primary_key=True, autoincrement=False )


class FriendsListsMemberAdded(Base,BaseTableMixin,FriendsListMixin,FriendMixin):
	__tablename__ = 'FriendsListsMemberAdded'

	__table_args__ = (
        PrimaryKeyConstraint('friends_list_id', 'target_id'),
    )

class FriendsListsMemberRemoved(Base,BaseTableMixin,FriendsListMixin,FriendMixin):
	__tablename__ = 'FriendsListsMemberRemoved'

	# Make sure we allow multiple removals
	__table_args__ = (
        PrimaryKeyConstraint('friends_list_id', 'target_id', 'timestamp'),
    )

class ContactsAdded(Base,BaseTableMixin,FriendMixin):
	__tablename__ = 'ContactsAdded'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'target_id'),
    )

class ContactsRemoved(Base,BaseTableMixin,FriendMixin):
	__tablename__ = 'ContactsRemoved'

	# Make sure we allow multiple contact drops
	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'target_id', 'timestamp'),
    )



def create_chat_initiated(user, nti_session, chat):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	cid = _chatid.get_id( chat )

	timestamp = get_created_timestamp( chat )

	new_object = ChatsInitiated( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									chat_id=cid )
	db.session.add( new_object )

def chat_joined(user, nti_session, timestamp, chat):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	cid = _chatid.get_id( chat )
	timestamp = timestamp_type( timestamp )

	new_object = ChatsJoined( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								chat_id=cid )
	db.session.add( new_object )
	try:
		db.session.flush()
	except IntegrityError:
		logger.debug( 'User (%s) already exists in chat (%s)', uid, chat )

# DFLs
def create_dynamic_friends_list(user, nti_session, dynamic_friends_list):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	dfl_id = _dflid.get_id( dynamic_friends_list )
	timestamp = get_created_timestamp( dynamic_friends_list )

	new_object = DynamicFriendsListsCreated( 	user_id=uid,
												session_id=sid,
												timestamp=timestamp,
												dfl_id=dfl_id )
	db.session.add( new_object )

# Note: with this and friends_list, we're leaving members in their
# (now deleted) groups.  This could be useful (or we can remove
# them at a later date).
def remove_dynamic_friends_list(timestamp, dfl_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_dfl = db.session.query(DynamicFriendsListsCreated).filter( DynamicFriendsListsCreated.dfl_id==dfl_id ).one()
	db_dfl.deleted=timestamp
	db.session.flush()

def create_dynamic_friends_member(user, nti_session, timestamp, dynamic_friends_list, new_friend ):
	db = get_analytics_db()
	if user is None:
		uid = None
	else:
		user = get_or_create_user(user )
		uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	dfl_id = _dflid.get_id( dynamic_friends_list )
	target = get_or_create_user(new_friend )
	target_id = target.user_id
	timestamp = timestamp_type( timestamp )

	new_object = DynamicFriendsListsMemberAdded( 	user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													dfl_id=dfl_id,
													target_id=target_id )
	db.session.add( new_object )

def _delete_dynamic_friend_list_member( db, dfl_id, target_id ):
	friend = db.session.query( DynamicFriendsListsMemberAdded ).filter(
										DynamicFriendsListsMemberAdded.dfl_id==dfl_id,
										DynamicFriendsListsMemberAdded.target_id==target_id ).first()
	db.session.delete( friend )

def remove_dynamic_friends_member(user, nti_session, timestamp, dynamic_friends_list, target ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	dfl_id = _dflid.get_id( dynamic_friends_list )
	target = get_or_create_user(target )
	target_id = target.user_id
	timestamp = timestamp_type( timestamp )

	new_object = DynamicFriendsListsMemberRemoved( 	user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													dfl_id=dfl_id,
													target_id=target_id )
	db.session.add( new_object )
	_delete_dynamic_friend_list_member( db, dfl_id, target_id )

# FLs
def create_friends_list(user, nti_session, timestamp, friends_list):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	friends_list_id = _flid.get_id( friends_list )
	timestamp = timestamp_type( timestamp )

	new_object = FriendsListsCreated( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										friends_list_id=friends_list_id )
	db.session.add( new_object )

def remove_friends_list(timestamp, friends_list_id):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	db_friends_list = db.session.query(FriendsListsCreated).filter( FriendsListsCreated.friends_list_id==friends_list_id ).one()
	db_friends_list.deleted=timestamp
	db.session.flush()

def _delete_friend_list_member( db, friends_list_id, target_id ):
	friend = db.session.query(FriendsListsMemberAdded).filter( 	FriendsListsMemberAdded.friends_list_id==friends_list_id,
																	FriendsListsMemberAdded.target_id==target_id ).first()
	db.session.delete( friend )

def _find_members( db, friends_list, members ):
	""" For a friends_list, return a tuple of members to add/remove. """
	members = set( [ x.target_id for x in members if x ] )
	new_members = set( [ get_or_create_user(x ).user_id for x in friends_list if x] )

	members_to_add = new_members - members
	members_to_remove = members - new_members

	return ( members_to_add, members_to_remove )

def _delete_contact_added( db, user_id, target_id ):
	contact = db.session.query(ContactsAdded).filter(
										ContactsAdded.user_id == user_id,
										ContactsAdded.target_id == target_id ).first()
	db.session.delete( contact )

def _get_friends_list_members( db, friends_list_id ):
	results = db.session.query(FriendsListsMemberAdded).filter(
								FriendsListsMemberAdded.friends_list_id == friends_list_id ).all()
	return results

def _get_contacts( db, uid ):
	results = db.session.query(ContactsAdded).filter(
								ContactsAdded.user_id == uid ).all()
	return results

def update_contacts( user, nti_session, timestamp, friends_list ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	timestamp = timestamp_type( timestamp )

	members = _get_contacts( db, uid )
	# This works because contacts are friends_list, and both
	# 'member' sets have 'target_id' columns we key off of.
	members_to_add, members_to_remove \
		= _find_members( db, friends_list, members )

	for new_member in members_to_add:
		new_object = ContactsAdded( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									target_id=new_member )

		db.session.add( new_object )
	for old_member in members_to_remove:
		new_object = ContactsRemoved( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										target_id=old_member )
		db.session.add( new_object )
		_delete_contact_added( db, uid, old_member )

	return len( members_to_add ) - len( members_to_remove )

def update_friends_list( user, nti_session, timestamp, friends_list ):
	db = get_analytics_db()
	friends_list_id = _flid.get_id( friends_list )
	members = _get_friends_list_members( db, friends_list_id )
	members_to_add, members_to_remove \
		= _find_members( db, friends_list, members )

	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	timestamp = timestamp_type( timestamp )

	for new_member in members_to_add:
		new_object = FriendsListsMemberAdded( 	user_id=uid,
												session_id=sid,
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=new_member )
		db.session.add( new_object )
	for old_member in members_to_remove:
		new_object = FriendsListsMemberRemoved( user_id=uid,
												session_id=sid,
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=old_member )
		db.session.add( new_object )
		_delete_friend_list_member( db, friends_list_id, old_member )

	return len( members_to_add ) - len( members_to_remove )
