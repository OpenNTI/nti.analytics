#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import unittest

from datetime import datetime

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
from hamcrest import has_items

from ..metadata import Users
from ..metadata import Sessions
from ..metadata import ChatsInitiated
from ..metadata import ChatsJoined
from ..metadata import DynamicFriendsListsCreated
from ..metadata import DynamicFriendsListsRemoved
from ..metadata import DynamicFriendsListsMemberAdded
from ..metadata import DynamicFriendsListsMemberRemoved
from ..metadata import FriendsListsCreated
from ..metadata import FriendsListsRemoved
from ..metadata import FriendsListsMemberAdded
from ..metadata import FriendsListsMemberRemoved
from ..metadata import ContactsAdded
from ..metadata import ContactsRemoved
from ..metadata import ThoughtsCreated
from ..metadata import ThoughtsViewed
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
from ..metadata import NoteCommentsCreated
from ..metadata import CourseCatalogViews
from ..metadata import EnrollmentTypes
from ..metadata import CourseEnrollments
from ..metadata import CourseDrops
from ..metadata import AssignmentsTaken
from ..metadata import AssignmentDetails
from ..metadata import SelfAssessmentsTaken
from ..metadata import SelfAssessmentDetails

from nti.analytics.database import database
from ..database import AnalyticsDB

from sqlalchemy.orm.exc import FlushError
from sqlalchemy.exc import IntegrityError

from nti.dataserver.users import User
from nti.dataserver.users import FriendsList

test_user_id = 01234
test_user_ds_id = 78
test_session_id = 56

class TestUsers(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		self.session = self.db.get_session()
		assert_that( self.db.engine.table_names(), has_length( 35 ) )
		
	def tearDown(self):
		self.session.close()	
				
	def test_users(self):
		results = self.session.query(Users).all()
		assert_that( results, has_length( 0 ) )
		
		fooser = User( 'foo1978' )
		
		self.db.create_user( self.session, fooser )

		results = self.session.query(Users).all()
		assert_that( results, has_length( 1 ) )
		
		new_user = self.session.query(Users).one()
		# Sequence generated
		assert_that( new_user.user_id, 1 )
		assert_that( new_user.user_ds_id, 101 )

		# Dupe, but not inserted
		self.db._get_or_create_user( self.session, fooser )	
		
		# And passing in just user ids
		self.db.create_user( self.session, 42 )
		results = self.session.query(Users).all()
		assert_that( results, has_length( 2 ) )
		
		# New
		self.db._get_or_create_user( self.session, 43 )	
		results = self.session.query(Users).all()
		assert_that( results, has_length( 3 ) )
		
		# Dupe insert
		with self.assertRaises(IntegrityError):
			self.db.create_user( self.session, fooser )
			
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
		self.db.create_session( self.session, user.user_id, object(), datetime.now(), '0.1.2.3.4', '0.9', 'webapp' )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )
		
		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, test_user_id )
		assert_that( new_session.session_id, test_session_id )
		assert_that( new_session.ip_addr, '0.1.2.3.4' )	
		assert_that( new_session.platform, 'webapp' )
		assert_that( new_session.version, '0.9' )	
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, none() )
		
		# End session
		self.db._end_session( self.session, object(), datetime.now() )
		results = self.session.query(Sessions).all()
		assert_that( results, has_length( 1 ) )
		
		new_session = self.session.query(Sessions).one()
		assert_that( new_session.user_id, test_user_id )
		assert_that( new_session.session_id, test_session_id )
		assert_that( new_session.ip_addr, '0.1.2.3.4' )	
		assert_that( new_session.platform, 'webapp' )
		assert_that( new_session.version, '0.9' )	
		assert_that( new_session.start_time, not_none() )
		assert_that( new_session.end_time, not_none() )

_User = namedtuple('_User', ('intid',))

class TestSocial(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		self.session = self.db.get_session()
		user = Users( user_id=test_user_id, user_ds_id=test_user_ds_id )
		self.session.add( user )
		
		db_session = Sessions( session_id=test_session_id, user_id=test_user_id, ip_addr='0.1.2.3.4', version='0.9', platform='webapp', start_time=datetime.now() )
		self.session.add( db_session )
		self.session.flush()

	def tearDown(self):
		self.session.close()	
		
	def test_chats(self):
		results = self.session.query( ChatsInitiated ).all()
		assert_that( results, has_length( 0 ) )
		
		new_chat = ChatsInitiated( session_id=test_session_id, user_id=test_user_id, timestamp=datetime.now(), chat_id=101 )
		self.session.add( new_chat )
		results = self.session.query(ChatsInitiated).all()
		assert_that( results, has_length( 1 ) )
		
		new_chat = self.session.query(ChatsInitiated).one()
		assert_that( new_chat.user_id, test_user_id )
		assert_that( new_chat.session_id, test_session_id )
		assert_that( new_chat.timestamp, 0 )	
		assert_that( new_chat.chat_id, 101 )	
	
class TestComments(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		self.session = self.db.get_session()
		user = Users( user_id=test_user_id, user_ds_id=test_user_ds_id )
		self.session.add( user )
		
		db_session = Sessions( session_id=test_session_id, user_id=test_user_id, ip_addr='0.1.2.3.4', version='webapp-0.9', start_time=datetime.now() )
		self.session.add( db_session )
		self.course_name='course1'
		self.create_forum_and_topic( self.course_name )	
	
	def tearDown(self):
		self.session.close()	
		
	def create_forum_and_topic(self,course_name):
		#Forum
		new_forum = ForumsCreated( 	session_id=test_session_id, 
									user_id=test_user_id, 
									timestamp=datetime.now(),
									forum_id='forum1',
									course_id=course_name )
		self.session.add( new_forum )
		
		#Discussion
		new_discussion = DiscussionsCreated( 	session_id=test_session_id, 
												user_id=test_user_id, 
												timestamp=datetime.now(),
												forum_id='forum1',
												discussion_id='discussion1',
												course_id=course_name )
		self.session.add( new_discussion )
		# FIXME finish this test
		
	def test_comments(self):
		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.db.get_forum_comments_for_user( self.session, user=_User(test_user_id), course_id=self.course_name)
		assert_that( results, has_length( 0 ) )
		
		new_comment = ForumCommentsCreated( session_id=test_session_id, 
											user_id=test_user_id, 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment1',
											course_id=self.course_name )
		self.session.add( new_comment )

		results = self.db.get_forum_comments_for_user( self.session, user=_User(test_user_id), course_id=self.course_name )
		assert_that( results, has_length( 1 ) )
		
		results = self.db.get_forum_comments_for_course( self.session, course_id=self.course_name )
		assert_that( results, has_length( 1 ) )
		
		result = results[0]
		assert_that( result.forum_id, 'forum1' )
		assert_that( result.discussion_id, 'discussion1' )
		assert_that( result.comment_id, 'comment1' )
		assert_that( result.session_id, test_session_id )
		assert_that( result.user_id, test_user_id )
		assert_that( result.course_id, self.course_name )
		
	def test_multiple_comments(self):
		results = self.db.get_forum_comments_for_user( self.session, user=_User(test_user_id), course_id=self.course_name )
		assert_that( results, has_length( 0 ) )
		
		new_comment1 = ForumCommentsCreated( session_id=test_session_id, 
											user_id=test_user_id, 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment1',
											course_id=self.course_name )
		new_comment2 = ForumCommentsCreated( session_id=test_session_id, 
											user_id=test_user_id, 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment2',
											deleted=datetime.now(),
											course_id=self.course_name )
		self.session.add( new_comment1 )
		self.session.add( new_comment2 )

		#Deleted comments not returned
		results = self.db.get_forum_comments_for_user( self.session, user=_User(test_user_id), course_id=self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, 'comment1' )
		
		results = self.db.get_forum_comments_for_course( self.session, course_id=self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, 'comment1' )
		
	def test_multiple_comments_users(self):
		results = self.db.get_forum_comments_for_user( self.session, user=_User(test_user_id), course_id=self.course_name )
		assert_that( results, has_length( 0 ) )
		
		#different user
		new_comment1 = ForumCommentsCreated( session_id=test_session_id, 
											user_id='test_user_2', 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment1',
											course_id=self.course_name )
		new_comment2 = ForumCommentsCreated( session_id=test_session_id, 
											user_id=test_user_id, 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment2',
											course_id=self.course_name )
		#deleted
		new_comment3 = ForumCommentsCreated( session_id=test_session_id, 
											user_id=test_user_id, 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment3',
											deleted=datetime.now(),
											course_id=self.course_name )
		#Different course
		new_comment4 = ForumCommentsCreated( session_id=test_session_id, 
											user_id=test_user_id, 
											timestamp=datetime.now(),
											forum_id='forum1',
											discussion_id='discussion1',
											comment_id='comment4',
											course_id='course_2' )
		self.session.add( new_comment1 )
		self.session.add( new_comment2 )
		self.session.add( new_comment3 )
		self.session.add( new_comment4 )

		#Deleted comments not returned
		results = self.db.get_forum_comments_for_user( self.session, user=_User(test_user_id), course_id=self.course_name )
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].comment_id, 'comment2' )
		
		results = self.db.get_forum_comments_for_course( self.session, course_id=self.course_name )
		assert_that( results, has_length( 2 ) )
		results = [x.comment_id for x in results]
		assert_that( results, has_items( 'comment1', 'comment2' ) )
	

