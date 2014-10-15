#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import fudge

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_items

from nti.dataserver.contenttypes.forums.post import CommentPost

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import boards as db_boards

from nti.analytics.database.boards import ForumsCreated
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import TopicsViewed
from nti.analytics.database.boards import ForumCommentsCreated

# For new objects, this is the default intid stored in the database.
# For subsequent objects, this will increase by one.
from . import DEFAULT_INTID

class TestForums(AnalyticsTestBase):

	def setUp(self):
		super( TestForums, self ).setUp()
		self.forum_id = 1
		self.forum_ds_id = 999

	def test_forums(self):
		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 0 ) )
		my_forum = MockForum( None, intid=self.forum_ds_id )
		# Create forum
		db_boards.create_forum( test_user_ds_id,
								test_session_id, self.course_id, my_forum )

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

	def test_idempotent(self):
		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 0 ) )

		my_forum = MockForum( None, intid=self.forum_ds_id )
		# Create forum
		db_boards.create_forum( test_user_ds_id,
								test_session_id, self.course_id, my_forum )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_boards.create_forum( test_user_ds_id,
								test_session_id, self.course_id, my_forum )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )

	def test_chain_delete(self):
		forum = MockForum( None, intid=self.forum_ds_id )
		topic = MockTopic( forum, intid=DEFAULT_INTID )
		db_boards.create_forum( 	test_user_ds_id,
								test_session_id, self.course_id, self.forum_ds_id )
		db_boards.create_topic( 	test_user_ds_id,
									test_session_id, self.course_id, topic )

		new_comment1 = MockComment( topic, intid=21 )
		new_comment2 = MockComment( topic, intid=22 )

		# Create relationships
		forum.children = [ topic ]
		topic.children = [ new_comment1, new_comment2 ]

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_id,
										topic, new_comment1 )

		db_boards.create_forum_comment( 	test_user_ds_id,
										test_session_id,
										self.course_id,
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
		self.course_id = 1
		self.forum_id = 1
		self.forum_ds_id = 999
		self.forum = MockForum( None, intid=self.forum_ds_id )
		db_boards.create_forum( test_user_ds_id,
								test_session_id, self.course_id, self.forum )

	def test_topics(self):
		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 0 ) )

		topic_id = 1
		topic_ds_id = DEFAULT_INTID
		my_topic = MockTopic( self.forum, intid=topic_ds_id )
		# Create topic
		db_boards.create_topic( test_user_ds_id,
								test_session_id, self.course_id, my_topic )

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
										self.course_id, my_topic,
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

	def test_idempotent(self):
		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 0 ) )

		topic_ds_id = DEFAULT_INTID
		my_topic = MockTopic( self.forum, intid=topic_ds_id )
		# Create topic
		db_boards.create_topic( test_user_ds_id,
								test_session_id, self.course_id, my_topic )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_boards.create_topic( test_user_ds_id,
								test_session_id, self.course_id, my_topic )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 1 ) )

	def test_idempotent_views(self):
		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 0 ) )

		topic_ds_id = DEFAULT_INTID
		my_topic = MockTopic( self.forum, intid=topic_ds_id )
		# Create topic
		db_boards.create_topic( test_user_ds_id,
								test_session_id, self.course_id, my_topic )

		event_time = datetime.now()
		time_length = 30
		db_boards.create_topic_view( test_user_ds_id,
										test_session_id, event_time,
										self.course_id, my_topic,
										time_length )

		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 1 ) )

		db_boards.create_topic_view( test_user_ds_id,
										test_session_id, event_time,
										self.course_id, my_topic,
										time_length )

		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 1 ) )

class TestForumComments(AnalyticsTestBase):

	def setUp(self):
		super( TestForumComments, self ).setUp()
		self.course_id = 1
		self.forum_id = 1
		self.forum_ds_id = 999
		self.topic_id = 1
		self.topic_ds_id = DEFAULT_INTID
		self.forum = MockForum( None, intid=self.forum_ds_id )
		self.topic = MockTopic( self.forum, intid=self.topic_ds_id  )
		db_boards.create_forum( 	test_user_ds_id,
								test_session_id, self.course_id, self.forum )
		db_boards.create_topic( 	test_user_ds_id,
									test_session_id, self.course_id, self.topic )

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_comments(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		# Topic parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )

		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments_for_course( self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = self.session.query( ForumCommentsCreated ).all()
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

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_idempotent(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )
		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_comment_with_parent(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		# Comment parent
		comment_id = DEFAULT_INTID
		# 2nd id lookup
		post_id = DEFAULT_INTID + 1
		my_comment = MockComment( CommentPost(), inReplyTo=post_id, intid=comment_id )

		db_boards.create_forum_comment( test_user_ds_id,
										test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments_for_course( self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = self.session.query( ForumCommentsCreated ).all()
		result = results[0]
		assert_that( result.forum_id, is_( self.forum_id ) )
		assert_that( result.topic_id, is_( self.topic_id ) )
		assert_that( result.comment_id, is_( comment_id ) )
		assert_that( result.session_id, is_( test_session_id ) )
		assert_that( result.user_id, is_( 1 ) )
		assert_that( result.course_id, is_( self.course_id ) )
		assert_that( result.parent_id, is_( post_id ) )
		assert_that( result.deleted, none() )

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_multiple_comments(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		new_comment1 = MockComment( self.topic, intid=19 )
		new_comment2 = MockComment( self.topic, intid=20 )

		db_boards.create_forum_comment( test_user_ds_id,
										test_session_id,
										self.course_id,
										self.topic, new_comment1 )

		db_boards.create_forum_comment( test_user_ds_id,
										test_session_id,
										self.course_id,
										self.topic, new_comment2 )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 2 ) )

		results = db_boards.get_forum_comments_for_course( self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 2 ) )

		#Deleted comments not returned
		db_boards.delete_forum_comment( datetime.now(), 20 )

		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].Comment, new_comment2 )

		results = db_boards.get_forum_comments_for_course( self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].Comment, new_comment2 )

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_multiple_comments_users(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		test_user_ds_id2 = 9999
		course_name2 = 'different course'

		new_comment1 = MockComment( self.topic, intid=19 )
		new_comment2 = MockComment( self.topic, intid=20 )
		new_comment3 = MockComment( self.topic, intid=21 )
		new_comment4 = MockComment( self.topic, intid=22 )

		# Different user
		db_boards.create_forum_comment( test_user_ds_id2,
										test_session_id,
										self.course_id,
										self.topic, new_comment1 )

		db_boards.create_forum_comment( test_user_ds_id,
										test_session_id,
										self.course_id,
										self.topic, new_comment2 )
		# Deleted
		db_boards.create_forum_comment( test_user_ds_id,
										test_session_id,
										self.course_id,
										self.topic, new_comment3 )
		db_boards.delete_forum_comment( datetime.now(), 21 )
		# Different course
		db_boards.create_forum_comment( test_user_ds_id,
										test_session_id,
										course_name2,
										self.topic, new_comment4 )

		# Only non-deleted comment for user in course
		results = db_boards.get_forum_comments_for_user( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].Comment, new_comment2 )

		results = db_boards.get_forum_comments_for_course( self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 2 ) )
		results = [x.Comment for x in results]
		assert_that( results, has_items( new_comment1, new_comment2 ) )


