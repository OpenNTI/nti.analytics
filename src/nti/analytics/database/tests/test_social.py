#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockParent

from nti.analytics.database import social as db_social

from nti.analytics.database.users import get_or_create_user

from nti.analytics.database.social import ChatsInitiated
from nti.analytics.database.social import ChatsJoined
from nti.analytics.database.social import DynamicFriendsListsCreated
from nti.analytics.database.social import DynamicFriendsListsMemberAdded
from nti.analytics.database.social import DynamicFriendsListsMemberRemoved
from nti.analytics.database.social import FriendsListsCreated
from nti.analytics.database.social import FriendsListsMemberAdded
from nti.analytics.database.social import FriendsListsMemberRemoved
from nti.analytics.database.social import ContactsAdded
from nti.analytics.database.social import ContactsRemoved
from nti.analytics.database.social import _get_contacts
from nti.analytics.database.social import _get_friends_list_members

class TestSocial(AnalyticsTestBase):

	def setUp(self):
		super( TestSocial, self ).setUp()

	def test_chats(self):
		results = self.session.query( ChatsInitiated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( ChatsJoined ).all()
		assert_that( results, has_length( 0 ) )

		test_chat_id = 1
		test_chat_ds_id = 999

		db_social.create_chat_initiated( test_user_ds_id, test_session_id, test_chat_ds_id )
		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 1 ) )

		new_chat = self.session.query(ChatsInitiated).one()
		assert_that( new_chat.user_id, is_( 1 ) )
		assert_that( new_chat.session_id, is_( test_session_id ) )
		assert_that( new_chat.timestamp, not_none() )
		assert_that( new_chat.chat_id, is_( test_chat_id ) )

		# Chat joined
		db_social.chat_joined( test_user_ds_id, test_session_id, datetime.now(), test_chat_ds_id )
		results = self.session.query(ChatsJoined).all()
		assert_that( results, has_length( 1 ) )

		new_chat = self.session.query(ChatsJoined).one()
		assert_that( new_chat.user_id, is_( 1 ) )
		assert_that( new_chat.session_id, is_( test_session_id ) )
		assert_that( new_chat.timestamp, not_none() )
		assert_that( new_chat.chat_id, is_( test_chat_id ) )

		# Update chat
		new_chat = MockParent( None, intid=test_chat_ds_id )
		new_occupants = ( 'quinton', 'elliot', 'alice', test_user_ds_id )
		db_social.update_chat( datetime.now(), new_chat, new_occupants )
		members = self.session.query(ChatsJoined).all()
		assert_that( members, has_length( 4 ) )

	def test_idempotent_chat(self):
		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 0 ) )

		test_chat_ds_id = 999
		db_social.create_chat_initiated( test_user_ds_id, test_session_id, test_chat_ds_id )

		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 1 ) )

		db_social.create_chat_initiated( test_user_ds_id, test_session_id, test_chat_ds_id )
		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 1 ) )


	def test_dfl(self):
		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberRemoved ).all()
		assert_that( results, has_length( 0 ) )

		test_dfl_ds_id = 999
		test_dfl_id = 1
		# Create DFL
		db_social.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_ds_id )
		results = self.session.query(DynamicFriendsListsCreated).all()
		assert_that( results, has_length( 1 ) )

		dfl = self.session.query(DynamicFriendsListsCreated).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )
		assert_that( dfl.deleted, none() )

		# Join DFL
		db_social.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_ds_id, test_user_ds_id )
		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 1 ) )

		dfl = self.session.query(DynamicFriendsListsMemberAdded).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.target_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )

		# Leave DFL
		db_social.remove_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_ds_id, test_user_ds_id )
		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query(DynamicFriendsListsMemberRemoved).all()
		assert_that( results, has_length( 1 ) )

		dfl = self.session.query(DynamicFriendsListsMemberRemoved).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.target_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )

		# Delete DFL
		db_social.remove_dynamic_friends_list( datetime.now(), test_dfl_ds_id )

		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 0 ) )

		dfl = self.session.query(DynamicFriendsListsCreated).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )
		assert_that( dfl.dfl_ds_id, none() )
		assert_that( dfl.deleted, not_none() )

	def test_idempotent_dfl(self):
		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )

		test_dfl_ds_id = 999
		# Create DFL
		db_social.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_ds_id )

		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_social.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_ds_id )

		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 1 ) )

	def test_dfl_multiple_members(self):
		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberRemoved ).all()
		assert_that( results, has_length( 0 ) )

		test_dfl_ds_id = 999
		test_dfl_ds_id2 = 1000
		# Create DFL
		db_social.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_ds_id )
		db_social.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_ds_id2 )
		results = self.session.query(DynamicFriendsListsCreated).all()
		assert_that( results, has_length( 2 ) )

		# Join DFLs; 3 dfl1, 1 dfl2
		db_social.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_ds_id, test_user_ds_id )
		db_social.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_ds_id, test_user_ds_id + 1 )
		db_social.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_ds_id, test_user_ds_id + 2)
		db_social.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_ds_id2, test_user_ds_id )
		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 4 ) )

		# Delete DFL1
		db_social.remove_dynamic_friends_list( datetime.now(), test_dfl_ds_id )
		results = self.session.query(DynamicFriendsListsCreated).all()
		assert_that( results, has_length( 2 ) )

		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 4 ) )

	def test_friends_list(self):
		results = self.session.query( FriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( FriendsListsMemberAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( FriendsListsMemberRemoved ).all()
		assert_that( results, has_length( 0 ) )

		test_fl_id = 1
		test_fl_ds_id = 999
		# Create FL
		db_social.create_friends_list( test_user_ds_id, test_session_id, datetime.now(), test_fl_ds_id )
		results = self.session.query(FriendsListsCreated).all()
		assert_that( results, has_length( 1 ) )

		fl = self.session.query(FriendsListsCreated).one()
		assert_that( fl.user_id, is_( 1 ) )
		assert_that( fl.session_id, is_( test_session_id ) )
		assert_that( fl.timestamp, not_none() )
		assert_that( fl.friends_list_id, is_( test_fl_id ) )
		assert_that( fl.deleted, none() )

		# Join FL
		friend1 = 999
		friend2 = 1000
		friend3 = 1001
		friends = [ friend1, friend2 ]
		fl = MockFL( None, intid=test_fl_ds_id, vals=friends )
		db_social.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )

		friend1_id = get_or_create_user( friend1 ).user_id
		friend2_id = get_or_create_user( friend2 ).user_id
		friend3_id = get_or_create_user( friend3 ).user_id

		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 2 ) )
		results = _get_friends_list_members( self.db, test_fl_id )
		assert_that( results, has_length( 2 ) )
		results = [x.target_id for x in results]
		assert_that( results, contains_inanyorder( friend1_id, friend2_id ) )

		# Add third friend
		friends.append( friend3 )
		db_social.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )
		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 3 ) )
		results = _get_friends_list_members( self.db, test_fl_id )
		assert_that( results, has_length( 3 ) )
		results = [x.target_id for x in results]
		assert_that( results, contains_inanyorder( friend1_id, friend2_id, friend3_id ) )

		# Leave FL
		friends.remove( friend1 )
		db_social.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )
		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 2 ) )
		results = _get_friends_list_members( self.db, test_fl_id )
		assert_that( results, has_length( 2 ) )
		results = [x.target_id for x in results]
		assert_that( results, contains_inanyorder( friend2_id, friend3_id ) )

		results = self.session.query(FriendsListsMemberRemoved).all()
		assert_that( results, has_length( 1 ) )

		friend_removed = self.session.query(FriendsListsMemberRemoved).one()
		assert_that( friend_removed.user_id, is_( 1 ) )
		assert_that( friend_removed.target_id, is_( friend1_id ) )
		assert_that( friend_removed.session_id, is_( test_session_id ) )
		assert_that( friend_removed.timestamp, not_none() )
		assert_that( friend_removed.friends_list_id, is_( test_fl_id ) )

		# Empty FL
		friends[:] = []
		db_social.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )
		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 0 ) )
		results = _get_friends_list_members( self.db, test_fl_id )
		assert_that( results, has_length( 0 ) )
		results = self.session.query(FriendsListsMemberRemoved).all()
		assert_that( results, has_length( 3 ) )

		# Delete FL
		db_social.remove_friends_list( datetime.now(), test_fl_ds_id )

		fl = self.session.query(FriendsListsCreated).one()
		assert_that( fl.user_id, is_( 1 ) )
		assert_that( fl.session_id, is_( test_session_id ) )
		assert_that( fl.timestamp, not_none() )
		assert_that( fl.friends_list_id, is_( test_fl_id ) )
		assert_that( fl.deleted, not_none() )
		assert_that( fl.friends_list_ds_id, none() )

	def test_idempotent_friends_list(self):
		results = self.session.query( FriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )

		test_fl_ds_id = 999
		event_time = datetime.now()
		# Create FL
		db_social.create_friends_list( test_user_ds_id, test_session_id, event_time, test_fl_ds_id )

		results = self.session.query( FriendsListsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_social.create_friends_list( test_user_ds_id, test_session_id, event_time, test_fl_ds_id )

		results = self.session.query( FriendsListsCreated ).all()
		assert_that( results, has_length( 1 ) )

	def test_contacts(self):
		results = self.session.query( ContactsAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( ContactsRemoved ).all()
		assert_that( results, has_length( 0 ) )

		# Add contact
		new_contact1 = 999
		new_contact2 = 1000
		contacts = [ new_contact1, new_contact2 ]
		result = db_social.update_contacts( test_user_ds_id, test_session_id, datetime.now(), contacts )
		results = self.session.query(ContactsAdded).all()
		assert_that( results, has_length( 2 ) )
		assert_that( result, is_( 2 ) )

		nc1_id = get_or_create_user( new_contact1 ).user_id
		nc2_id = get_or_create_user( new_contact2 ).user_id

		db_contacts = _get_contacts( self.db, uid=1 )
		assert_that( db_contacts, has_length( 2 ) )
		db_contacts = [x.target_id for x in db_contacts]
		assert_that( db_contacts, contains_inanyorder( nc1_id, nc2_id ) )

		# Remove contact
		contacts = [ new_contact1 ]
		result = db_social.update_contacts( test_user_ds_id, test_session_id, datetime.now(), contacts )
		assert_that( result, is_( -1 ) )
		results = self.session.query(ContactsAdded).all()
		assert_that( results, has_length( 1 ) )
		results = self.session.query(ContactsRemoved).all()
		assert_that( results, has_length( 1 ) )

		# new_contact2 removed
		contact_removed = self.session.query(ContactsRemoved).one()
		assert_that( contact_removed.user_id, is_( 1 ) )
		assert_that( contact_removed.target_id, is_( nc2_id ) )
		assert_that( contact_removed.session_id, is_( test_session_id ) )
		assert_that( contact_removed.timestamp, not_none() )

		# Empty contacts
		contacts = []
		result = db_social.update_contacts( test_user_ds_id, test_session_id, datetime.now(), contacts )
		assert_that( result, is_( -1 ) )
		results = self.session.query(ContactsAdded).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query(ContactsRemoved).all()
		assert_that( results, has_length( 2 ) )

		db_contacts = _get_contacts( self.db, uid=1 )
		assert_that( db_contacts, has_length( 0 ) )
