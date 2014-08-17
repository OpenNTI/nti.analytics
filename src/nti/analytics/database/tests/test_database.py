#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest
import fudge

from zope import component

from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import has_items

from sqlalchemy.exc import IntegrityError

from nti.dataserver.contenttypes.forums.post import CommentPost

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB

from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import users as db_users
from nti.analytics.database import assessments as db_assessments
from nti.analytics.database import blogs as db_blogs
from nti.analytics.database import boards as db_boards
from nti.analytics.database import enrollments as db_enrollments
from nti.analytics.database import resource_tags as db_tags
from nti.analytics.database import resource_views as db_views
from nti.analytics.database import social as db_social


from nti.analytics.database.users import Users
from nti.analytics.database.users import Sessions
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
from nti.analytics.database.blogs import BlogsCreated
from nti.analytics.database.blogs import BlogsViewed
from nti.analytics.database.resource_views import CourseResourceViews
from nti.analytics.database.resource_views import VideoEvents
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NotesViewed
from nti.analytics.database.resource_tags import HighlightsCreated
from nti.analytics.database.boards import ForumsCreated
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import TopicsViewed
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.enrollments import CourseCatalogViews
from nti.analytics.database.enrollments import EnrollmentTypes
from nti.analytics.database.enrollments import CourseEnrollments
from nti.analytics.database.enrollments import CourseDrops
from nti.analytics.database.assessments import AssignmentsTaken
from nti.analytics.database.assessments import AssignmentDetails
from nti.analytics.database.assessments import AssignmentGrades
from nti.analytics.database.assessments import AssignmentDetailGrades
from nti.analytics.database.assessments import SelfAssessmentsTaken

test_user_id = 	1234
test_user_ds_id = 78
test_session_id = '56'

# For new objects, this is the default intid stored in the database.
# For subsequent objects, this will increase by one.
from . import DEFAULT_INTID

class TestUsers(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://', testmode=True )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session
		assert_that( self.db.engine.table_names(), has_length( 36 ) )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()

	def test_users(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )

		fooser = 2001

		db_users.create_user( fooser )

		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )

		new_user = self.session.query(Users).one()
		# Sequence generated
		assert_that( new_user.user_id, is_( 1 ) )
		assert_that( new_user.user_ds_id, is_( fooser ) )
		assert_that( new_user.shareable, is_( False ) )

		# Dupe, but not inserted
		get_or_create_user( fooser )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )

		# And passing in just user ids
		db_users.create_user( 42 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 2 ) )

		# New
		get_or_create_user( 43 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 3 ) )

		# Save everything we have.
		self.session.commit()

	def test_user_constraints(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )

		# A None user_ds_id is now perfectly valid.
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
		db_users.create_session( test_user_ds_id, test_session_id, datetime.now(), '0.1.2.3.4', 'webapp', '0.9' )
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
		db_users.end_session( test_session_id, datetime.now() )
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
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session
		db_users.create_user( test_user_ds_id )
		db_users.create_session( test_user_ds_id, test_session_id, datetime.now(), '0.1.2.3.4', 'webapp', '0.9' )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()

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

	def test_create_blog(self):
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Add blog
		new_blog_id = 1
		new_blog_ds_id = 999
		new_blog = MockParent( None, intid=new_blog_ds_id )
		db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog = self.session.query( BlogsCreated ).one()
		assert_that( blog.user_id, is_( 1 ) )
		assert_that( blog.blog_id, is_( new_blog_id ) )
		assert_that( blog.session_id, is_( test_session_id ) )
		assert_that( blog.timestamp, not_none() )
		assert_that( blog.deleted, none() )

		# Create blog view
		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 0 ) )

		db_blogs.create_blog_view( test_user_ds_id, test_session_id, datetime.now(), new_blog, 18 )
		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )

		blog = self.session.query( BlogsViewed ).one()
		assert_that( blog.user_id, is_( 1 ) )
		assert_that( blog.blog_id, is_( new_blog_id ) )
		assert_that( blog.session_id, is_( test_session_id ) )
		assert_that( blog.timestamp, not_none() )
		assert_that( blog.time_length, is_( 18 ) )

		# Delete
		db_blogs.delete_blog( datetime.now(), new_blog_ds_id )
		blog = self.session.query( BlogsCreated ).one()
		assert_that( blog.blog_id, is_( new_blog_id ) )
		assert_that( blog.deleted, not_none() )
		assert_that( blog.blog_ds_id, none() )

class TestCourseResources(AnalyticsTestBase):

	def setUp(self):
		super( TestCourseResources, self ).setUp()
		self.course_name='course1'
		self.course_id = 1 #seq insert
		self.context_path_flat = 'dashboard'
		self.context_path= [ 'dashboard' ]

	def test_resource_view(self):
		results = self.session.query( CourseResourceViews ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		time_length = 30
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, datetime.now(),
											self.course_name, self.context_path,
											resource_id, time_length )
		results = self.session.query(CourseResourceViews).all()
		assert_that( results, has_length( 1 ) )

		resource_view = self.session.query(CourseResourceViews).one()
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( self.context_path_flat ) )
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
		db_views.create_video_event( test_user_ds_id,
									test_session_id, datetime.now(),
									self.course_name, self.context_path,
									resource_id, time_length,
									video_event_type, video_start_time,
									video_end_time,  with_transcript )
		results = self.session.query(VideoEvents).all()
		assert_that( results, has_length( 1 ) )

		resource_view = self.session.query(VideoEvents).one()
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( self.context_path_flat ) )
		assert_that( resource_view.resource_id, is_( resource_id ) )
		assert_that( resource_view.video_event_type, is_( video_event_type ) )
		assert_that( resource_view.video_start_time, is_( video_start_time ) )
		assert_that( resource_view.video_end_time, is_( video_end_time ) )
		assert_that( resource_view.time_length, is_( time_length ) )
		assert_that( resource_view.with_transcript )

	@fudge.patch( 'nti.analytics.database.resource_tags._get_sharing_enum' )
	def test_note(self, mock_sharing_enum):
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		note_id = 1
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )

		# Create note
		db_tags.create_note( 	test_user_ds_id,
								test_session_id, self.course_name, my_note )

		results = db_tags.get_notes_created_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_id ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( resource_id ) )
		# 'UNKNOWN' since we cannot access course and it's scopes.
		assert_that( note.sharing, is_( 'UNKNOWN' ) )
		assert_that( note.deleted, none() )
		assert_that( note.timestamp, not_none() )

		# Note view
		db_tags.create_note_view( 	test_user_ds_id,
									test_session_id, datetime.now(),
									self.course_name, my_note )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesViewed).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_id ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( resource_id ) )
		assert_that( note.timestamp, not_none() )

		# Delete note
		db_tags.delete_note( datetime.now(), note_ds_id )

		results = self.session.query(NotesCreated).all()
		assert_that( results, has_length( 1 ) )

		results = db_tags.get_notes_created_for_course( self.course_name )
		assert_that( results, has_length( 0 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.deleted, not_none() )

	def test_highlight(self):
		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		highlight_ds_id = DEFAULT_INTID
		highlight_id = 1
		my_highlight = MockHighlight( resource_id, intid=highlight_ds_id, containerId=resource_id )

		# Create highlight
		db_tags.create_highlight( 	test_user_ds_id,
									test_session_id, self.course_name, my_highlight )

		results = db_tags.get_highlights_created_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.user_id, is_( 1 ) )
		assert_that( highlight.session_id, is_( test_session_id ) )
		assert_that( highlight.course_id, is_( self.course_id ) )
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.resource_id, is_( resource_id ) )
		assert_that( highlight.deleted, none() )
		assert_that( highlight.timestamp, not_none() )

		# Delete highlight
		db_tags.delete_highlight( datetime.now(), highlight_ds_id )

		results = self.session.query(HighlightsCreated).all()
		assert_that( results, has_length( 1 ) )

		results = db_tags.get_highlights_created_for_course( self.course_name )
		assert_that( results, has_length( 0 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.deleted, not_none() )
		assert_that( highlight.highlight_ds_id, none() )

class TestForums(AnalyticsTestBase):

	def setUp(self):
		super( TestForums, self ).setUp()
		self.course_name='course1'
		self.course_id = 1
		self.forum_id = 1
		self.forum_ds_id = 999

	def test_forums(self):
		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 0 ) )
		my_forum = MockForum( None, intid=self.forum_ds_id )
		# Create forum
		db_boards.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, my_forum )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )

		forum = self.session.query(ForumsCreated).one()
		assert_that( forum.user_id, is_( 1 ) )
		assert_that( forum.session_id, is_( test_session_id ) )
		assert_that( forum.course_id, is_( self.course_id ) )
		assert_that( forum.forum_id, is_( self.forum_id ) )
		assert_that( forum.timestamp, not_none() )
		assert_that( forum.deleted, none() )

		# Delete forum
		db_boards.delete_forum( datetime.now(), self.forum_ds_id )

		results = self.session.query(ForumsCreated).all()
		assert_that( results, has_length( 1 ) )

		forum = self.session.query(ForumsCreated).one()
		assert_that( forum.forum_id, is_( self.forum_id ) )
		assert_that( forum.forum_ds_id, none() )
		assert_that( forum.deleted, not_none() )
		assert_that( forum.forum_ds_id, none() )

	def test_chain_delete(self):
		forum = MockForum( None, intid=self.forum_ds_id )
		topic = MockTopic( forum, intid=DEFAULT_INTID )
		db_boards.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, self.forum_ds_id )
		db_boards.create_topic( 	test_user_ds_id,
									test_session_id, self.course_name, topic )

		new_comment1 = MockComment( topic, intid=21 )
		new_comment2 = MockComment( topic, intid=22 )

		# Create relationships
		forum.children = [ topic ]
		topic.children = [ new_comment1, new_comment2 ]

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										topic, new_comment1 )

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										topic, new_comment2 )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, none() )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, none() )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 2 ) )
		assert_that( results[0].deleted, none() )
		assert_that( results[1].deleted, none() )

		# Delete forum and everything goes with it
		db_boards.delete_forum( datetime.now(), self.forum_ds_id )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, not_none() )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].deleted, not_none() )
		assert_that( results[0].topic_ds_id, none() )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 2 ) )
		assert_that( results[0].deleted, not_none() )
		assert_that( results[1].deleted, not_none() )

class TestTopics(AnalyticsTestBase):

	def setUp(self):
		super( TestTopics, self ).setUp()
		self.course_name = 'course1'
		self.course_id = 1
		self.forum_id = 1
		self.forum_ds_id = 999
		self.forum = MockForum( None, intid=self.forum_ds_id )
		db_boards.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, self.forum )

	def test_topics(self):
		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 0 ) )

		topic_id = 1
		topic_ds_id = DEFAULT_INTID
		my_topic = MockTopic( self.forum, intid=topic_ds_id )
		# Create topic
		db_boards.create_topic( 	test_user_ds_id,
									test_session_id, self.course_name, my_topic )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 1 ) )

		topic = self.session.query( TopicsCreated ).one()
		assert_that( topic.user_id, is_( 1 ) )
		assert_that( topic.session_id, is_( test_session_id ) )
		assert_that( topic.course_id, is_( self.course_id ) )
		assert_that( topic.forum_id, is_( self.forum_id ) )
		assert_that( topic.topic_id, is_( topic_id ) )
		assert_that( topic.timestamp, not_none() )
		assert_that( topic.deleted, none() )

		# View topic
		time_length = 30
		db_boards.create_topic_view( test_user_ds_id,
										test_session_id, datetime.now(),
										self.course_name, my_topic,
										time_length )

		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 1 ) )

		topic = self.session.query( TopicsViewed ).one()
		assert_that( topic.user_id, is_( 1 ) )
		assert_that( topic.session_id, is_( test_session_id ) )
		assert_that( topic.course_id, is_( self.course_id ) )
		assert_that( topic.forum_id, is_( self.forum_id ) )
		assert_that( topic.topic_id, is_( topic_id ) )
		assert_that( topic.timestamp, not_none() )
		assert_that( topic.time_length, is_( 30 ) )

		# Delete topic
		db_boards.delete_topic( datetime.now(), topic_ds_id )

		results = self.session.query(TopicsCreated).all()
		assert_that( results, has_length( 1 ) )

		topic = self.session.query(TopicsCreated).one()
		assert_that( topic.topic_id, is_( topic_id ) )
		assert_that( topic.deleted, not_none() )
		assert_that( topic.topic_ds_id, none() )

class TestForumComments(AnalyticsTestBase):

	def setUp(self):
		super( TestForumComments, self ).setUp()
		self.course_name='course1'
		self.course_id = 1
		self.forum_id = 1
		self.forum_ds_id = 999
		self.topic_id = 1
		self.topic_ds_id = DEFAULT_INTID
		self.forum = MockForum( None, intid=self.forum_ds_id )
		self.topic = MockTopic( self.forum, intid=self.topic_ds_id  )
		db_boards.create_forum( 	test_user_ds_id,
								test_session_id, self.course_name, self.forum )
		db_boards.create_topic( 	test_user_ds_id,
									test_session_id, self.course_name, self.topic )

	def test_comments(self):
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		# Topic parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )

		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_name,
										self.topic, my_comment )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		result = results[0]
		assert_that( result.forum_id, is_( self.forum_id ) )
		assert_that( result.topic_id, is_( self.topic_id ) )
		assert_that( result.comment_id, is_( comment_id ) )
		assert_that( result.session_id, is_( test_session_id ) )
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.course_id, is_( self.course_id ) )
		assert_that( result.parent_id, none() )
		assert_that( result.deleted, none() )


	def test_comment_with_parent(self):
		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		# Comment parent
		comment_id = DEFAULT_INTID
		# 2nd id lookup
		post_id = DEFAULT_INTID + 1
		my_comment = MockComment( CommentPost(), inReplyTo=post_id, intid=comment_id )

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id, self.course_name,
										self.topic, my_comment )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )

		result = results[0]
		assert_that( result.forum_id, is_( self.forum_id ) )
		assert_that( result.topic_id, is_( self.topic_id ) )
		assert_that( result.comment_id, is_( comment_id ) )
		assert_that( result.session_id, is_( test_session_id ) )
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.course_id, is_( self.course_id ) )
		assert_that( result.parent_id, is_( post_id ) )
		assert_that( result.deleted, none() )

	def test_multiple_comments(self):
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		new_comment1 = MockComment( self.topic, intid=19 )
		new_comment2 = MockComment( self.topic, intid=20 )

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.topic, new_comment1 )

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.topic, new_comment2 )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 2 ) )

		results = db_boards.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 2 ) )

		#Deleted comments not returned
		db_boards.delete_forum_comment( datetime.now(), 20 )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, new_comment2.intid )

		results = db_boards.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, new_comment2.intid )

	def test_multiple_comments_users(self):
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 0 ) )

		test_user_ds_id2 = 9999
		course_name2 = 'different course'

		new_comment1 = MockComment( self.topic, intid=19 )
		new_comment2 = MockComment( self.topic, intid=20 )
		new_comment3 = MockComment( self.topic, intid=21 )
		new_comment4 = MockComment( self.topic, intid=22 )

		# Different user
		db_boards.create_forum_comment( 	test_user_ds_id2,
										test_session_id,
										self.course_name,
										self.topic, new_comment1 )

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.topic, new_comment2 )
		# Deleted
		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_name,
										self.topic, new_comment3 )
		db_boards.delete_forum_comment( datetime.now(), 21 )
		# Different course
		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										course_name2,
										self.topic, new_comment4 )

		# Only non-deleted comment for user in course
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, new_comment2.intid )

		results = db_boards.get_forum_comments_for_course( self.course_name )
		assert_that( results, has_length( 2 ) )
		results = [x.comment_id for x in results]
		assert_that( results, has_items( new_comment1.intid, new_comment2.intid ) )

class TestBlogComments(AnalyticsTestBase):

	def setUp(self):
		super( TestBlogComments, self ).setUp()
		self.blog_ds_id = 999
		self.blog_id = 1
		new_blog = MockParent( None, intid=self.blog_ds_id )
		db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )

	def tearDown(self):
		self.session.close()

	def test_comments(self):
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Empty parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( MockThought( None ), intid=comment_id )

		db_blogs.create_blog_comment( test_user_ds_id, test_session_id, self.blog_ds_id, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.session_id, is_( test_session_id ) )
		assert_that( blog_comment.user_id, is_( 1 ) )
		assert_that( blog_comment.parent_id, none() )
		assert_that( blog_comment.deleted, none() )

		db_blogs.delete_blog_comment( datetime.now(), comment_id )
		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.deleted, not_none() )

	def test_chain_delete(self):
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Empty parent
		my_comment = MockComment( MockThought( None ) )

		db_blogs.create_blog_comment( test_user_ds_id, test_session_id, self.blog_ds_id, my_comment )

		db_blogs.delete_blog( datetime.now(), self.blog_ds_id )

		blog = self.session.query( BlogsCreated ).one()
		assert_that( blog.deleted, not_none() )

		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.deleted, not_none() )

	def test_comment_with_parent(self):
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Comment parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( CommentPost(), inReplyTo=CommentPost(), intid=comment_id )

		db_blogs.create_blog_comment( test_user_ds_id, test_session_id, self.blog_ds_id, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.session_id, is_( test_session_id ) )
		assert_that( blog_comment.user_id, is_( 1 ) )
		assert_that( blog_comment.parent_id, not_none() )
		assert_that( blog_comment.deleted, none() )

		db_blogs.delete_blog_comment( datetime.now(), comment_id )
		blog_comment = self.session.query( BlogCommentsCreated ).one()
		assert_that( blog_comment.blog_id, is_( self.blog_id ) )
		assert_that( blog_comment.comment_id, is_( comment_id ) )
		assert_that( blog_comment.deleted, not_none() )

class TestCourseViews(AnalyticsTestBase):

	def setUp(self):
		super( TestCourseViews, self ).setUp()
		self.course_name='course1'
		self.course_id = 1

	def test_course_catalog_views(self):
		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 0 ) )

		time_length = 30
		db_enrollments.create_course_catalog_view( test_user_ds_id, test_session_id, datetime.now(), self.course_name, time_length )

		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 1 ) )

		catalog_view = self.session.query( CourseCatalogViews ).one()
		assert_that( catalog_view.session_id, is_( test_session_id ) )
		assert_that( catalog_view.user_id, is_( 1 ) )
		assert_that( catalog_view.course_id, is_( self.course_id ) )
		assert_that( catalog_view.time_length, is_( time_length ) )
		assert_that( catalog_view.timestamp, not_none() )

	def test_enrollment(self):
		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 0 ) )

		for_credit = 'for_credit'
		db_enrollments.create_course_enrollment( test_user_ds_id, test_session_id, datetime.now(), self.course_name, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )

		enrollment = self.session.query( CourseEnrollments ).one()
		assert_that( enrollment.session_id, is_( test_session_id ) )
		assert_that( enrollment.user_id, is_( 1 ) )
		assert_that( enrollment.course_id, is_( self.course_id ) )
		assert_that( enrollment.timestamp, not_none() )
		assert_that( enrollment.type_id, is_( 1 ) )

		# EnrollmentType
		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 1 ) )

		enrollment_type = self.session.query( EnrollmentTypes ).one()
		assert_that( enrollment_type.type_name, is_( for_credit ) )

		# Another enrollment
		db_enrollments.create_course_enrollment( test_user_ds_id + 1, test_session_id, datetime.now(), self.course_name, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 2 ) )

		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 1 ) )

		# Drop
		db_enrollments.create_course_drop( test_user_ds_id, test_session_id, datetime.now(), self.course_name )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )

		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 1 ) )
		drop = self.session.query( CourseDrops ).one()
		assert_that( drop.session_id, is_( test_session_id ) )
		assert_that( drop.user_id, is_( 1 ) )
		assert_that( drop.course_id, is_( self.course_id ) )
		assert_that( drop.timestamp, not_none() )

class TestAssessments(AnalyticsTestBase):

	def test_grade(self):
		# Could be a lot of types: 7, 7/10, 95, 95%, A-, 90 A
		from nti.analytics.database.assessments import _get_grade

		grade_num = _get_grade( 100 )
		assert_that( grade_num, is_( 100 ) )

		grade_num = _get_grade( 98.6 )
		assert_that( grade_num, is_( 98.6 ) )

		grade_num = _get_grade( '98 -' )
		assert_that( grade_num, is_( 98 ) )

		# We don't handle this yet.
		grade_num = _get_grade( '90 A' )
		assert_that( grade_num, none() )

