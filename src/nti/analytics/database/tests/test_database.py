#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from datetime import datetime
from datetime import timedelta

from collections import namedtuple

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import has_items

from sqlalchemy.exc import IntegrityError

from . import MockParent
MockFL = MockNote = MockHighlight = MockDiscussion = MockComment = MockThought = MockForum = MockParent

from ..metadata import Users
from ..metadata import Sessions
from ..metadata import ChatsInitiated
from ..metadata import ChatsJoined
from ..metadata import DynamicFriendsListsCreated
from ..metadata import DynamicFriendsListsMemberAdded
from ..metadata import DynamicFriendsListsMemberRemoved
from ..metadata import FriendsListsCreated
from ..metadata import FriendsListsMemberAdded
from ..metadata import FriendsListsMemberRemoved
from ..metadata import ContactsAdded
from ..metadata import ContactsRemoved
from ..metadata import BlogsCreated
from ..metadata import BlogsViewed
from ..metadata import CourseResourceViews
from ..metadata import VideoEvents
from ..metadata import NotesCreated
from ..metadata import NotesViewed
from ..metadata import HighlightsCreated
from ..metadata import ForumsCreated
from ..metadata import DiscussionsCreated
from ..metadata import DiscussionsViewed
from ..metadata import ForumCommentsCreated
from ..metadata import BlogCommentsCreated
from ..metadata import CourseCatalogViews
from ..metadata import EnrollmentTypes
from ..metadata import CourseEnrollments
from ..metadata import CourseDrops
from ..metadata import AssignmentsTaken
from ..metadata import AssignmentDetails
from ..metadata import AssignmentGrades
from ..metadata import AssignmentDetailGrades
from ..metadata import SelfAssessmentsTaken

from ..database import AnalyticsDB

from nti.dataserver.users import User
from nti.dataserver.users import FriendsList

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.post import CommentPost

from nti.contenttypes.courses import courses

test_user_id = 	1234
test_user_ds_id = 78
test_session_id = '56'

# For new objects, this is the default intid stored in the database.
# For subsequent objects, this will increase by one.
from . import DEFAULT_INTID

class TestUsers(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		self.session = self.db.session
		assert_that( self.db.engine.table_names(), has_length( 34 ) )

	def tearDown(self):
		self.session.close()

	def test_users(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )

		fooser = 2001

		self.db.create_user( fooser )

		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )

		new_user = self.session.query(Users).one()
		# Sequence generated
		assert_that( new_user.user_id, is_( 1 ) )
		assert_that( new_user.user_ds_id, is_( fooser ) )

		# Dupe, but not inserted
		self.db._get_or_create_user( fooser )

		# And passing in just user ids
		self.db.create_user( 42 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 2 ) )

		# New
		self.db._get_or_create_user( 43 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 3 ) )

		# Idempotent
		self.db.create_user( fooser )

	def test_user_constraints(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )

		with self.assertRaises(IntegrityError):
			new_user = Users( user_ds_id=None )
			self.session.add( new_user )
			self.session.flush()

	def test_sessions(self):
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 0 ) )

		user = Users( user_ds_id=test_user_ds_id )
		self.session.add( user )
		self.session.flush()

		# Using new generated user_id
		self.db.create_session( test_user_ds_id, test_session_id, datetime.now(), '0.1.2.3.4', 'webapp', '0.9' )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( test_session_id ) )
		assert_that( new_session.ip_addr, is_( '0.1.2.3.4' ) )
		assert_that( new_session.platform, is_( 'webapp' ) )
		assert_that( new_session.version, is_( '0.9' ) )
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, none() )

		# End session
		self.db.end_session( test_session_id, datetime.now() )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )

		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, is_( user.user_id ) )
		assert_that( new_session.session_id, is_( test_session_id ) )
		assert_that( new_session.ip_addr, is_( '0.1.2.3.4' ) )
		assert_that( new_session.platform, is_( 'webapp' ) )
		assert_that( new_session.version, is_( '0.9' ) )
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, not_none() )

class AnalyticsTestBase(unittest.TestCase):
	""" A base class that simply creates a user and session"""

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		self.session = self.db.session
		self.db.create_user( test_user_ds_id )
		self.db.create_session( test_user_ds_id, test_session_id, datetime.now(), '0.1.2.3.4', 'webapp', '0.9' )

class TestSocial(AnalyticsTestBase):

	def setUp(self):
		super( TestSocial, self ).setUp()

	def tearDown(self):
		self.session.close()

	def test_chats(self):
		results = self.session.query( ChatsInitiated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( ChatsJoined ).all()
		assert_that( results, has_length( 0 ) )

		test_chat_id = 999

		self.db.create_chat_initiated( test_user_ds_id, test_session_id, test_chat_id )
		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 1 ) )

		new_chat = self.session.query(ChatsInitiated).one()
		assert_that( new_chat.user_id, is_( 1 ) )
		assert_that( new_chat.session_id, is_( test_session_id ) )
		assert_that( new_chat.timestamp, not_none() )
		assert_that( new_chat.chat_id, is_( test_chat_id ) )

		# Chat joined
		self.db.chat_joined( test_user_ds_id, test_session_id, datetime.now(), test_chat_id )
		results = self.session.query(ChatsJoined).all()
		assert_that( results, has_length( 1 ) )

		new_chat = self.session.query(ChatsJoined).one()
		assert_that( new_chat.user_id, is_( 1 ) )
		assert_that( new_chat.session_id, is_( test_session_id ) )
		assert_that( new_chat.timestamp, not_none() )
		assert_that( new_chat.chat_id, is_( test_chat_id ) )


	def test_dfl(self):
		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberRemoved ).all()
		assert_that( results, has_length( 0 ) )

		test_dfl_id = 999
		# Create DFL
		self.db.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_id )
		results = self.session.query(DynamicFriendsListsCreated).all()
		assert_that( results, has_length( 1 ) )

		dfl = self.session.query(DynamicFriendsListsCreated).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )
		assert_that( dfl.deleted, none() )

		# Join DFL
		self.db.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_id, test_user_ds_id )
		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 1 ) )

		dfl = self.session.query(DynamicFriendsListsMemberAdded).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.target_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )

		# Leave DFL
		self.db.remove_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_id, test_user_ds_id )
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
		self.db.remove_dynamic_friends_list( datetime.now(), test_dfl_id )

		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 0 ) )

		dfl = self.session.query(DynamicFriendsListsCreated).one()
		assert_that( dfl.user_id, is_( 1 ) )
		assert_that( dfl.session_id, is_( test_session_id ) )
		assert_that( dfl.timestamp, not_none() )
		assert_that( dfl.dfl_id, is_( test_dfl_id ) )
		assert_that( dfl.deleted, not_none() )

	def test_dfl_multiple_members(self):
		results = self.session.query( DynamicFriendsListsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DynamicFriendsListsMemberRemoved ).all()
		assert_that( results, has_length( 0 ) )

		test_dfl_id = 999
		test_dfl_id2 = 1000
		# Create DFL
		self.db.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_id )
		self.db.create_dynamic_friends_list( test_user_ds_id, test_session_id, test_dfl_id2 )
		results = self.session.query(DynamicFriendsListsCreated).all()
		assert_that( results, has_length( 2 ) )

		# Delete empty DFL
		self.db.remove_dynamic_friends_list( datetime.now(), test_dfl_id )
		results = self.session.query(DynamicFriendsListsCreated).all()
		assert_that( results, has_length( 2 ) )

		# Join DFLs; 3 dfl1, 1 dfl2
		self.db.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_id, test_user_ds_id )
		self.db.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_id, test_user_ds_id + 1 )
		self.db.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_id, test_user_ds_id + 2)
		self.db.create_dynamic_friends_member( test_user_ds_id, test_session_id, datetime.now(), test_dfl_id2, test_user_ds_id )
		results = self.session.query(DynamicFriendsListsMemberAdded).all()
		assert_that( results, has_length( 4 ) )

		# Delete DFL1
		self.db.remove_dynamic_friends_list( datetime.now(), test_dfl_id )
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

		test_fl_id = 999
		# Create FL
		self.db.create_friends_list( test_user_ds_id, test_session_id, datetime.now(), test_fl_id )
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
		fl = MockFL( None, intid=test_fl_id, vals=friends )
		self.db.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )

		friend1_id = self.db._get_or_create_user( friend1 ).user_id
		friend2_id = self.db._get_or_create_user( friend2 ).user_id
		friend3_id = self.db._get_or_create_user( friend3 ).user_id

		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 2 ) )
		results = self.db._get_friends_list_members( test_fl_id )
		assert_that( results, has_length( 2 ) )
		results = [x.target_id for x in results]
		assert_that( results, contains_inanyorder( friend1_id, friend2_id ) )

		# Add third friend
		friends.append( friend3 )
		self.db.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )
		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 3 ) )
		results = self.db._get_friends_list_members( test_fl_id )
		assert_that( results, has_length( 3 ) )
		results = [x.target_id for x in results]
		assert_that( results, contains_inanyorder( friend1_id, friend2_id, friend3_id ) )

		# Leave FL
		friends.remove( friend1 )
		self.db.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )
		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 2 ) )
		results = self.db._get_friends_list_members( test_fl_id )
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
		self.db.update_friends_list( test_user_ds_id, test_session_id, datetime.now(), fl )
		results = self.session.query(FriendsListsMemberAdded).all()
		assert_that( results, has_length( 0 ) )
		results = self.db._get_friends_list_members( test_fl_id )
		assert_that( results, has_length( 0 ) )
		results = self.session.query(FriendsListsMemberRemoved).all()
		assert_that( results, has_length( 3 ) )

		# Delete FL
		self.db.remove_friends_list( datetime.now(), test_fl_id )

		fl = self.session.query(FriendsListsCreated).one()
		assert_that( fl.user_id, is_( 1 ) )
		assert_that( fl.session_id, is_( test_session_id ) )
		assert_that( fl.timestamp, not_none() )
		assert_that( fl.friends_list_id, is_( test_fl_id ) )
		assert_that( fl.deleted, not_none() )

	def test_contacts(self):
		results = self.session.query( ContactsAdded ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( ContactsRemoved ).all()
		assert_that( results, has_length( 0 ) )

		# Add contact
		new_contact1 = 999
		new_contact2 = 1000
		contacts = [ new_contact1, new_contact2 ]
		result = self.db.update_contacts( test_user_ds_id, test_session_id, datetime.now(), contacts )
		results = self.session.query(ContactsAdded).all()
		assert_that( results, has_length( 2 ) )
		assert_that( result, is_( 2 ) )

		nc1_id = self.db._get_or_create_user( new_contact1 ).user_id
		nc2_id = self.db._get_or_create_user( new_contact2 ).user_id

		db_contacts = self.db._get_contacts( uid=1 )
		assert_that( db_contacts, has_length( 2 ) )
		db_contacts = [x.target_id for x in db_contacts]
		assert_that( db_contacts, contains_inanyorder( nc1_id, nc2_id ) )

		# Remove contact
		contacts = [ new_contact1 ]
		result = self.db.update_contacts( test_user_ds_id, test_session_id, datetime.now(), contacts )
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
		result = self.db.update_contacts( test_user_ds_id, test_session_id, datetime.now(), contacts )
		assert_that( result, is_( -1 ) )
		results = self.session.query(ContactsAdded).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query(ContactsRemoved).all()
		assert_that( results, has_length( 2 ) )

		db_contacts = self.db._get_contacts( uid=1 )
		assert_that( db_contacts, has_length( 0 ) )

	def test_create_blog(self):
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Add blog
		new_blog_id = 999
		self.db.create_blog( test_user_ds_id, test_session_id, new_blog_id )
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog = self.session.query( BlogsCreated ).one()
		assert_that( blog.user_id, is_( 1 ) )
		assert_that( blog.blog_id, is_( new_blog_id ) )
		assert_that( blog.session_id, is_( test_session_id ) )
		assert_that( blog.timestamp, not_none() )
		assert_that( blog.deleted, none() )

		# Delete
		self.db.delete_blog( datetime.now(), new_blog_id )
		assert_that( blog.blog_id, is_( new_blog_id ) )
		assert_that( blog.deleted, not_none() )

		# Create blog view
		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 0 ) )

		self.db.create_blog_view( test_user_ds_id, test_session_id, datetime.now(), new_blog_id )
		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )

		blog = self.session.query( BlogsViewed ).one()
		assert_that( blog.user_id, is_( 1 ) )
		assert_that( blog.blog_id, is_( 999 ) )
		assert_that( blog.session_id, is_( test_session_id ) )
		assert_that( blog.timestamp, not_none() )

class TestCourseResources(AnalyticsTestBase):

	def setUp(self):
		super( TestCourseResources, self ).setUp()
		self.course_name='course1'
		self.context_path='overview'

	def tearDown(self):
		self.session.close()

	def test_resource_view(self):
		results = self.session.query( CourseResourceViews ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		time_length = 30
		self.db.create_course_resource_view( test_user_ds_id,
											test_session_id, datetime.now(),
											self.course_name, self.context_path,
											resource_id, time_length )
		results = self.session.query(CourseResourceViews).all()
		assert_that( results, has_length( 1 ) )

		resource_view = self.session.query(CourseResourceViews).one()
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_name ) )
		assert_that( resource_view.context_path, is_( self.context_path ) )
		assert_that( resource_view.resource_id, is_( resource_id ) )
		assert_that( resource_view.time_length, is_( time_length ) )

	def test_video_view(self):
		results = self.session.query( VideoEvents ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_video'
		time_length = 30
		video_event_type = 'WATCH'
		video_start_time = 30
		video_end_time = 60
		with_transcript = True
		self.db.create_video_event( test_user_ds_id,
									test_session_id, datetime.now(),
									self.course_name, self.context_path,
									time_length,
									video_event_type, video_start_time,
									video_end_time, resource_id, with_transcript )
		results = self.session.query(VideoEvents).all()
		assert_that( results, has_length( 1 ) )

		resource_view = self.session.query(VideoEvents).one()
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_name ) )
		assert_that( resource_view.context_path, is_( self.context_path ) )
		assert_that( resource_view.resource_id, is_( resource_id ) )
		assert_that( resource_view.video_event_type, is_( video_event_type ) )
		assert_that( resource_view.video_start_time, is_( video_start_time ) )
		assert_that( resource_view.video_end_time, is_( video_end_time ) )
		assert_that( resource_view.time_length, is_( time_length ) )
		assert_that( resource_view.with_transcript )

	def test_note(self):
		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		note_id = DEFAULT_INTID
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_id )

		# Create note
		self.db.create_note( 	test_user_ds_id,
								test_session_id, self.course_name, my_note )

		results = self.db.get_notes_created_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_name ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( resource_id ) )
		# 'UNKNOWN' since we cannot access course and it's scopes.
		assert_that( note.sharing, is_( 'UNKNOWN' ) )
		assert_that( note.deleted, none() )
		assert_that( note.timestamp, not_none() )

		# Note view
		self.db.create_note_view( 	test_user_ds_id,
									test_session_id, datetime.now(),
									self.course_name, my_note )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesViewed).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_name ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( resource_id ) )
		assert_that( note.timestamp, not_none() )

		# Delete note
		self.db.delete_note( datetime.now(), note_id )

		results = self.session.query(NotesCreated).all()
		assert_that( results, has_length( 1 ) )

		results = self.db.get_notes_created_for_course( self.course_name )
		assert_that( results, has_length( 0 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.deleted, not_none() )

	def test_highlight(self):
		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		highlight_id = DEFAULT_INTID
		my_highlight = MockHighlight( resource_id, intid=highlight_id, containerId=resource_id )

		# Create highlight
		self.db.create_highlight( 	test_user_ds_id,
									test_session_id, self.course_name, my_highlight )

		results = self.db.get_highlights_created_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.user_id, is_( 1 ) )
		assert_that( highlight.session_id, is_( test_session_id ) )
		assert_that( highlight.course_id, is_( self.course_name ) )
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.resource_id, is_( resource_id ) )
		assert_that( highlight.deleted, none() )
		assert_that( highlight.timestamp, not_none() )

		# Delete highlight
		self.db.delete_highlight( datetime.now(), highlight_id )

		results = self.session.query(HighlightsCreated).all()
		assert_that( results, has_length( 1 ) )

		results = self.db.get_highlights_created_for_course( self.course_name )
		assert_that( results, has_length( 0 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.deleted, not_none() )

class TestForums(AnalyticsTestBase):

	def setUp(self):
		super( TestForums, self ).setUp()
		self.course_name='course1'
		self.forum_id = 999

	def tearDown(self):
		self.session.close()

	def test_forums(self):
		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 0 ) )
		my_forum = MockForum( None, intid=self.forum_id )
		# Create forum
		self.db.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, my_forum )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )

		forum = self.session.query(ForumsCreated).one()
		assert_that( forum.user_id, is_( 1 ) )
		assert_that( forum.session_id, is_( test_session_id ) )
		assert_that( forum.course_id, is_( self.course_name ) )
		assert_that( forum.forum_id, is_( self.forum_id ) )
		assert_that( forum.timestamp, not_none() )
		assert_that( forum.deleted, none() )

		# Delete forum
		self.db.delete_forum( datetime.now(), my_forum )

		results = self.session.query(ForumsCreated).all()
		assert_that( results, has_length( 1 ) )

		forum = self.session.query(ForumsCreated).one()
		assert_that( forum.forum_id, is_( self.forum_id ) )
		assert_that( forum.deleted, not_none() )

	def test_chain_delete(self):
		forum = MockForum( None, intid=self.forum_id )
		discussion = MockDiscussion( forum, intid=DEFAULT_INTID )
		self.db.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, self.forum_id )
		self.db.create_discussion( 	test_user_ds_id,
									test_session_id, self.course_name, MockDiscussion( self.forum_id ) )

		new_comment1 = MockComment( discussion, intid=21 )
		new_comment2 = MockComment( discussion, intid=22 )

		# Create relationships
		forum.children = [ discussion ]
		discussion.children = [ new_comment1, new_comment2 ]

		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										discussion, new_comment1 )

		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										discussion, new_comment2 )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, none() )

		results = self.session.query( DiscussionsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, none() )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 2 ) )
		assert_that( results[0].deleted, none() )
		assert_that( results[1].deleted, none() )

		# Delete forum and everything goes with it
		self.db.delete_forum( datetime.now(), forum )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, not_none() )

		results = self.session.query( DiscussionsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, not_none() )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 2 ) )
		assert_that( results[0].deleted, not_none() )
		assert_that( results[1].deleted, not_none() )

class TestDiscussions(AnalyticsTestBase):

	def setUp(self):
		super( TestDiscussions, self ).setUp()
		self.course_name = 'course1'
		self.forum_id = 999
		self.forum = MockForum( None, intid=self.forum_id )
		self.db.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, self.forum )

	def tearDown(self):
		self.session.close()

	def test_discussions(self):
		results = self.session.query( DiscussionsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( DiscussionsViewed ).all()
		assert_that( results, has_length( 0 ) )

		discussion_id = DEFAULT_INTID
		my_discussion = MockDiscussion( self.forum, intid=discussion_id )
		# Create discussion
		self.db.create_discussion( 	test_user_ds_id,
									test_session_id, self.course_name, my_discussion )

		results = self.session.query( DiscussionsCreated ).all()
		assert_that( results, has_length( 1 ) )

		discussion = self.session.query( DiscussionsCreated ).one()
		assert_that( discussion.user_id, is_( 1 ) )
		assert_that( discussion.session_id, is_( test_session_id ) )
		assert_that( discussion.course_id, is_( self.course_name ) )
		assert_that( discussion.forum_id, is_( self.forum_id ) )
		assert_that( discussion.discussion_id, is_( discussion_id ) )
		assert_that( discussion.timestamp, not_none() )
		assert_that( discussion.deleted, none() )

		# View discussion
		time_length = 30
		self.db.create_discussion_view( test_user_ds_id,
										test_session_id, datetime.now(),
										self.course_name, my_discussion,
										time_length )

		results = self.session.query( DiscussionsViewed ).all()
		assert_that( results, has_length( 1 ) )

		discussion = self.session.query( DiscussionsViewed ).one()
		assert_that( discussion.user_id, is_( 1 ) )
		assert_that( discussion.session_id, is_( test_session_id ) )
		assert_that( discussion.course_id, is_( self.course_name ) )
		assert_that( discussion.forum_id, is_( self.forum_id ) )
		assert_that( discussion.discussion_id, is_( discussion_id ) )
		assert_that( discussion.timestamp, not_none() )
		assert_that( discussion.time_length, is_( 30 ) )

		# Delete discussion
		self.db.delete_discussion( datetime.now(), my_discussion )

		results = self.session.query(DiscussionsCreated).all()
		assert_that( results, has_length( 1 ) )

		discussion = self.session.query(DiscussionsCreated).one()
		assert_that( discussion.discussion_id, is_( discussion_id ) )
		assert_that( discussion.deleted, not_none() )

class TestForumComments(AnalyticsTestBase):

	def setUp(self):
		super( TestForumComments, self ).setUp()
		self.course_name='course1'
		self.forum_id = 999
		self.discussion_id = DEFAULT_INTID
		forum = MockForum( None, intid=self.forum_id )
		self.discussion = MockDiscussion( forum, intid=self.discussion_id  )
		self.db.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, self.forum_id )
		self.db.create_discussion( 	test_user_ds_id,
									test_session_id, self.course_name, MockDiscussion( self.forum_id ) )

	def tearDown(self):
		self.session.close()

	def test_comments(self):
		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		# Discussion parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.discussion, intid=comment_id )

		self.db.create_forum_comment( 	test_user_ds_id, test_session_id, self.course_name,
										self.discussion, my_comment )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )

		results = self.db.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		result = results[0]
		assert_that( result.forum_id, is_( self.forum_id ) )
		assert_that( result.discussion_id, is_( self.discussion_id ) )
		assert_that( result.comment_id, is_( comment_id ) )
		assert_that( result.session_id, is_( test_session_id ) )
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.course_id, is_( self.course_name ) )
		assert_that( result.parent_id, none() )
		assert_that( result.deleted, none() )


	def test_comment_with_parent(self):
		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		# Comment parent
		comment_id = DEFAULT_INTID
		# 2nd id lookup
		post_id = DEFAULT_INTID + 1
		my_comment = MockComment( CommentPost(), inReplyTo=post_id, intid=comment_id )

		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id, self.course_name,
										self.discussion, my_comment )

		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )

		results = self.db.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		result = results[0]
		assert_that( result.forum_id, is_( self.forum_id ) )
		assert_that( result.discussion_id, is_( self.discussion_id ) )
		assert_that( result.comment_id, is_( comment_id ) )
		assert_that( result.session_id, is_( test_session_id ) )
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.course_id, is_( self.course_name ) )
		assert_that( result.parent_id, is_( post_id ) )
		assert_that( result.deleted, none() )

	def test_multiple_comments(self):
		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		new_comment1 = MockComment( self.discussion, intid=19 )
		new_comment2 = MockComment( self.discussion, intid=20 )

		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.discussion, new_comment1 )

		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.discussion, new_comment2 )

		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 2 ) )

		results = self.db.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 2 ) )

		#Deleted comments not returned
		self.db.delete_forum_comment( datetime.now(), new_comment1 )

		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, new_comment2.intid )

		results = self.db.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, new_comment2.intid )

	def test_multiple_comments_users(self):
		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		test_user_ds_id2 = 9999
		course_name2 = 'different course'

		new_comment1 = MockComment( self.discussion, intid=19 )
		new_comment2 = MockComment( self.discussion, intid=20 )
		new_comment3 = MockComment( self.discussion, intid=21 )
		new_comment4 = MockComment( self.discussion, intid=22 )

		# Different user
		self.db.create_forum_comment( 	test_user_ds_id2,
										test_session_id,
										self.course_name,
										self.discussion, new_comment1 )

		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.discussion, new_comment2 )
		# Deleted
		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.discussion, new_comment3 )
		self.db.delete_forum_comment( datetime.now(), new_comment3 )
		# Different course
		self.db.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										course_name2,
										self.discussion, new_comment4 )

		# Only non-deleted comment for user in course
		results = self.db.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, new_comment2.intid )

		results = self.db.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 2 ) )
		results = [x.comment_id for x in results]
		assert_that( results, has_items( new_comment1.intid, new_comment2.intid ) )

class TestBlogComments(AnalyticsTestBase):

	def setUp(self):
		super( TestBlogComments, self ).setUp()
		self.blog_id = 999
		self.db.create_blog( test_user_ds_id, test_session_id, self.blog_id )

	def tearDown(self):
		self.session.close()

	def test_comments(self):
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Empty parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( MockThought( None ) )

		self.db.create_blog_comment( test_user_ds_id, test_session_id, self.blog_id, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.session_id, is_( test_session_id ) )
		assert_that( blog_comment.user_id, is_( 1 ) )
		assert_that( blog_comment.parent_id, none() )
		assert_that( blog_comment.deleted, none() )

		self.db.delete_blog_comment( datetime.now(), comment_id )
		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.deleted, not_none() )


	def test_comment_with_parent(self):
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Comment parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( CommentPost(), inReplyTo=CommentPost() )

		self.db.create_blog_comment( test_user_ds_id, test_session_id, self.blog_id, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.session_id, is_( test_session_id ) )
		assert_that( blog_comment.user_id, is_( 1 ) )
		assert_that( blog_comment.parent_id, not_none() )
		assert_that( blog_comment.deleted, none() )

		self.db.delete_blog_comment( datetime.now(), comment_id )
		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.deleted, not_none() )

class TestCourseViews(AnalyticsTestBase):

	def setUp(self):
		super( TestCourseViews, self ).setUp()
		self.course_name='course1'

	def tearDown(self):
		self.session.close()

	def test_course_catalog_views(self):
		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 0 ) )

		time_length = 30
		self.db.create_course_catalog_view( test_user_ds_id, test_session_id, datetime.now(), self.course_name, time_length )

		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 1 ) )

		catalog_view = self.session.query( CourseCatalogViews ).one()
		assert_that( catalog_view.session_id, is_( test_session_id ) )
		assert_that( catalog_view.user_id, is_( 1 ) )
		assert_that( catalog_view.course_id, is_( self.course_name ) )
		assert_that( catalog_view.time_length, is_( time_length ) )
		assert_that( catalog_view.timestamp, not_none() )

	def test_enrollment(self):
		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 0 ) )

		for_credit = 'for_credit'
		self.db.create_course_enrollment( test_user_ds_id, test_session_id, datetime.now(), self.course_name, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )

		enrollment = self.session.query( CourseEnrollments ).one()
		assert_that( enrollment.session_id, is_( test_session_id ) )
		assert_that( enrollment.user_id, is_( 1 ) )
		assert_that( enrollment.course_id, is_( self.course_name ) )
		assert_that( enrollment.timestamp, not_none() )
		assert_that( enrollment.type_id, is_( 1 ) )
		assert_that( enrollment.dropped, none() )

		# EnrollmentType
		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 1 ) )

		enrollment_type = self.session.query( EnrollmentTypes ).one()
		assert_that( enrollment_type.type_name, is_( for_credit ) )

		# Another enrollment
		self.db.create_course_enrollment( test_user_ds_id + 1, test_session_id, datetime.now(), self.course_name, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 2 ) )

		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 1 ) )

		# Drop
		self.db.create_course_drop( test_user_ds_id, test_session_id, datetime.now(), self.course_name )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 2 ) )

		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 1 ) )
		drop = self.session.query( CourseDrops ).one()
		assert_that( drop.session_id, is_( test_session_id ) )
		assert_that( drop.user_id, is_( 1 ) )
		assert_that( drop.course_id, is_( self.course_name ) )
		assert_that( drop.timestamp, not_none() )

		enrollment = self.session.query( CourseEnrollments ).filter( CourseEnrollments.user_id == 1, CourseEnrollments.course_id==self.course_name ).one()
		assert_that( enrollment.session_id, is_( test_session_id ) )
		assert_that( enrollment.user_id, is_( 1 ) )
		assert_that( enrollment.course_id, is_( self.course_name ) )
		assert_that( enrollment.timestamp, not_none() )
		assert_that( enrollment.type_id, is_( 1 ) )
		assert_that( enrollment.dropped, not_none() )
