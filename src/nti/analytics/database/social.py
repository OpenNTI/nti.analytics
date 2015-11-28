#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics_database.social import ChatsJoined
from nti.analytics_database.social import ContactsAdded
from nti.analytics_database.social import ChatsInitiated
from nti.analytics_database.social import ContactsRemoved
from nti.analytics_database.social import FriendsListsCreated
from nti.analytics_database.social import FriendsListsMemberAdded
from nti.analytics_database.social import FriendsListsMemberRemoved
from nti.analytics_database.social import DynamicFriendsListsCreated
from nti.analytics_database.social import DynamicFriendsListsMemberAdded
from nti.analytics_database.social import DynamicFriendsListsMemberRemoved

from ..common import timestamp_type
from ..common import get_created_timestamp

from ..identifier import get_ds_id

from ._utils import get_filtered_records

from .users import get_user_db_id
from .users import get_or_create_user

from . import resolve_objects
from . import get_analytics_db

def _get_chat_id(db, chat_ds_id):
	chat = db.session.query(ChatsInitiated).filter(
							ChatsInitiated.chat_ds_id == chat_ds_id).first()
	return chat and chat.chat_id

_chat_exists = _get_chat_id

def create_chat_initiated(user, nti_session, chat):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	uid = user_record.user_id
	sid = nti_session
	chat_ds_id = get_ds_id(chat)

	if _chat_exists(db, chat_ds_id):
		logger.warn('Chat already exists (ds_id=%s) (owner=%s)', chat_ds_id, user)
		return

	timestamp = get_created_timestamp(chat)

	new_object = ChatsInitiated(user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								chat_ds_id=chat_ds_id)
	db.session.add(new_object)

def chat_joined(user, nti_session, timestamp, chat):
	db = get_analytics_db()
	user = get_or_create_user(user)
	uid = user.user_id
	sid = nti_session
	chat_ds_id = get_ds_id(chat)
	chat_id = _get_chat_id(db, chat_ds_id)
	timestamp = timestamp_type(timestamp)

	new_object = ChatsJoined(user_id=uid,
							 session_id=sid,
							 timestamp=timestamp,
							 chat_id=chat_id)
	db.session.add(new_object)

def _get_chat_members(db, chat_id):
	results = db.session.query(ChatsJoined).filter(
								ChatsJoined.chat_id == chat_id).all()
	return results

def update_chat(timestamp, chat, new_members):
	db = get_analytics_db()
	timestamp = timestamp_type(timestamp)
	chat_ds_id = get_ds_id(chat)
	chat_id = _get_chat_id(db, chat_ds_id)

	old_members = _get_chat_members(db, chat_id)
	old_members = set([x.user_id for x in old_members])
	members_to_add, _ = _find_members(new_members, old_members)

	for new_member in members_to_add:
		new_object = ChatsJoined(user_id=new_member,
								 session_id=None,
								 timestamp=timestamp,
								 chat_id=chat_id)

		db.session.add(new_object)

	return len(members_to_add)

# DFLs
def _get_dfl(db, dfl_ds_id):
	dfl = db.session.query(DynamicFriendsListsCreated).filter(
						   DynamicFriendsListsCreated.dfl_ds_id == dfl_ds_id).first()
	return dfl

def _get_dfl_id(db, dfl_ds_id):
	dfl = _get_dfl(db, dfl_ds_id)
	return dfl and dfl.dfl_id

_dfl_exists = _get_dfl_id

def create_dynamic_friends_list(user, nti_session, dynamic_friends_list):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	uid = user_record.user_id
	sid = nti_session
	dfl_ds_id = get_ds_id(dynamic_friends_list)

	if _dfl_exists(db, dfl_ds_id):
		logger.warn('DFL already exists (dfl_id=%s) (owner=%s)', dfl_ds_id, user)
		return

	timestamp = get_created_timestamp(dynamic_friends_list)

	new_object = DynamicFriendsListsCreated(user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											dfl_ds_id=dfl_ds_id)
	db.session.add(new_object)

# Note: with this and friends_list, we're leaving members in their
# (now deleted) groups.  This could be useful (or we can remove
# them at a later date).
def remove_dynamic_friends_list(timestamp, dfl_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type(timestamp)
	db_dfl = db.session.query(DynamicFriendsListsCreated).filter(
							  DynamicFriendsListsCreated.dfl_ds_id == dfl_ds_id).first()
	if not db_dfl:
		logger.info('DFL never created (%s)', dfl_ds_id)
		return
	db_dfl.deleted = timestamp
	db_dfl.dfl_ds_id = None
	db.session.flush()

def create_dynamic_friends_member(user, nti_session, timestamp, dynamic_friends_list, new_friend):
	db = get_analytics_db()
	if user is None:
		uid = None
	else:
		user = get_or_create_user(user)
		uid = user.user_id
	sid = nti_session
	dfl_ds_id = get_ds_id(dynamic_friends_list)
	dfl_id = _get_dfl_id(db, dfl_ds_id)
	target = get_or_create_user(new_friend)
	target_id = target.user_id
	timestamp = timestamp_type(timestamp)

	new_object = DynamicFriendsListsMemberAdded(user_id=uid,
												session_id=sid,
												timestamp=timestamp,
												dfl_id=dfl_id,
												target_id=target_id)
	db.session.add(new_object)

def _delete_dynamic_friend_list_member(db, dfl_id, target_id):
	friend = db.session.query(DynamicFriendsListsMemberAdded).filter(
							  DynamicFriendsListsMemberAdded.dfl_id == dfl_id,
							  DynamicFriendsListsMemberAdded.target_id == target_id).first()
	db.session.delete(friend)

def remove_dynamic_friends_member(user, nti_session, timestamp, dynamic_friends_list, target):
	db = get_analytics_db()
	user = get_or_create_user(user)
	uid = user.user_id
	sid = nti_session
	dfl_ds_id = get_ds_id(dynamic_friends_list)
	dfl_id = _get_dfl_id(db, dfl_ds_id)
	target = get_or_create_user(target)
	target_id = target.user_id
	timestamp = timestamp_type(timestamp)

	new_object = DynamicFriendsListsMemberRemoved(user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													dfl_id=dfl_id,
													target_id=target_id)
	db.session.add(new_object)
	_delete_dynamic_friend_list_member(db, dfl_id, target_id)

# FLs
def _get_friends_list_id(db, friends_list_ds_id):
	friends_list = db.session.query(FriendsListsCreated).filter(
									FriendsListsCreated.friends_list_ds_id == friends_list_ds_id).first()
	return friends_list and friends_list.friends_list_id

_friends_list_exists = _get_friends_list_id

def create_friends_list(user, nti_session, timestamp, friends_list):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	uid = user_record.user_id
	sid = nti_session
	friends_list_ds_id = get_ds_id(friends_list)

	if _friends_list_exists(db, friends_list_ds_id):
		logger.warn('Friends list already exists (ds_id=%s) (owner=%s)',
					friends_list_ds_id, user)
		return

	timestamp = timestamp_type(timestamp)

	new_object = FriendsListsCreated(user_id=uid,
									 session_id=sid,
									 timestamp=timestamp,
									 friends_list_ds_id=friends_list_ds_id)
	db.session.add(new_object)

def remove_friends_list(timestamp, friends_list_ds_id):
	db = get_analytics_db()
	timestamp = timestamp_type(timestamp)
	db_friends_list = db.session.query(FriendsListsCreated).filter(
									   FriendsListsCreated.friends_list_ds_id == friends_list_ds_id).first()
	if not db_friends_list:
		logger.info('FriendsList never created (%s)', friends_list_ds_id)
		return

	db_friends_list.deleted = timestamp
	db_friends_list.friends_list_ds_id = None
	db.session.flush()

def _delete_friend_list_member(db, friends_list_id, target_id):
	friend = db.session.query(FriendsListsMemberAdded).filter(
									FriendsListsMemberAdded.friends_list_id == friends_list_id,
									 FriendsListsMemberAdded.target_id == target_id).first()
	db.session.delete(friend)

def _find_friends_list_members(user_list, members):
	"""
	For a user_list, return a tuple of members to add/remove.
	"""
	members = set([ x.target_id for x in members if x ])
	return _find_members(user_list, members)

def _find_members(user_list, members):
	"""
	For a user_list, return a tuple of members to add/remove.
	"""
	members = set(members)
	new_members = set([ get_or_create_user(x).user_id for x in user_list if x])

	members_to_add = new_members - members
	members_to_remove = members - new_members

	return (members_to_add, members_to_remove)

def _delete_contact_added(db, user_id, target_id):
	contact = db.session.query(ContactsAdded).filter(
							   ContactsAdded.user_id == user_id,
							   ContactsAdded.target_id == target_id).first()
	db.session.delete(contact)

def _get_friends_list_members(db, friends_list_id):
	results = db.session.query(FriendsListsMemberAdded).filter(
							   FriendsListsMemberAdded.friends_list_id == friends_list_id).all()
	return results

def _get_contacts(db, uid):
	results = db.session.query(ContactsAdded).filter(
								ContactsAdded.user_id == uid).all()
	return results

def update_contacts(user, nti_session, timestamp, friends_list):
	db = get_analytics_db()
	user = get_or_create_user(user)
	uid = user.user_id
	sid = nti_session
	timestamp = timestamp_type(timestamp)

	members = _get_contacts(db, uid)
	members_to_add, members_to_remove \
		 = _find_friends_list_members(friends_list, members)

	for new_member in members_to_add:
		new_object = ContactsAdded(	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									target_id=new_member)

		db.session.add(new_object)
	for old_member in members_to_remove:
		new_object = ContactsRemoved(user_id=uid,
									 session_id=sid,
									 timestamp=timestamp,
									 target_id=old_member)
		db.session.add(new_object)
		_delete_contact_added(db, uid, old_member)

	return len(members_to_add) - len(members_to_remove)

def update_friends_list(user, nti_session, timestamp, friends_list):
	"""
	For the given friends list, update the members information.  This
	includes both adding and removing members.
	"""
	db = get_analytics_db()
	friends_list_ds_id = get_ds_id(friends_list)
	friends_list_id = _get_friends_list_id(db, friends_list_ds_id)

	if not friends_list_id:
		create_friends_list(user, nti_session, timestamp, friends_list)
		logger.info('Creating friends list (user=%s) (friends_list=%s) (ds_id=%s)',
					user, friends_list, friends_list_ds_id)
		friends_list_id = _get_friends_list_id(db, friends_list_ds_id)

	members = _get_friends_list_members(db, friends_list_id)
	members_to_add, members_to_remove \
		 = _find_friends_list_members(friends_list, members)

	user = get_or_create_user(user)
	uid = user.user_id
	sid = nti_session
	timestamp = timestamp_type(timestamp)

	for new_member in members_to_add:
		new_object = FriendsListsMemberAdded(user_id=uid,
											 session_id=sid,
											 timestamp=timestamp,
											 friends_list_id=friends_list_id,
											 target_id=new_member)
		db.session.add(new_object)
	for old_member in members_to_remove:
		new_object = FriendsListsMemberRemoved(	user_id=uid,
												session_id=sid,
												timestamp=timestamp,
												friends_list_id=friends_list_id,
												target_id=old_member)
		db.session.add(new_object)
		_delete_friend_list_member(db, friends_list_id, old_member)

	return len(members_to_add) - len(members_to_remove)

def _resolve_contact(row, user=None):
	if user is not None:
		row.user = user
	return row

def get_contacts_added(user, **kwargs):
	"""
	Fetch any contacts added for a user *after* the optionally given
	timestamp.
	"""
	results = get_filtered_records(user, ContactsAdded, **kwargs)
	return resolve_objects(_resolve_contact, results, user=user)

def _resolve_group(row, user=None):
	if user is not None:
		row.user = user
	return row

def _resolve_group_joined(row):
	# Just get our group record
	_, group_row = row
	group = _resolve_group(group_row)
	return group

def get_groups_created(user, get_deleted=False, **kwargs):
	"""
	Fetch any groups created by a user *after* the optionally given timestamp.
	"""
	filters = None
	if not get_deleted:
		filters = (DynamicFriendsListsCreated.deleted == None,)

	results = get_filtered_records(	user, DynamicFriendsListsCreated,
									filters=filters, **kwargs)
	return resolve_objects(_resolve_group, results, user=user)

def get_groups_joined(user, timestamp=None, max_timestamp=None):
	"""
	Fetch any groups joined by a user *after* the optionally given timestamp.
	"""
	# TODO Is this what we want? Or do we want groups that
	# the user only joined themselves?
	# Also, any groups this guy created will not be returned.
	results = ()
	db = get_analytics_db()
	user_id = get_user_db_id(user)
	if user_id:
		filters = [ DynamicFriendsListsMemberAdded.target_id == user_id ]
		if timestamp is not None:
			filters.append(DynamicFriendsListsMemberAdded.timestamp >= timestamp)
		if max_timestamp is not None:
			filters.append(DynamicFriendsListsMemberAdded.timestamp <= max_timestamp)
		groups = db.session.query(DynamicFriendsListsMemberAdded,
								  DynamicFriendsListsCreated).join(
											DynamicFriendsListsCreated).filter(*filters).all()
		results = resolve_objects(_resolve_group_joined, groups)
	return results
