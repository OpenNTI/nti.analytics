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

from nti.dataserver.users.users import Principal
from nti.dataserver.contenttypes.forums.post import CommentPost

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import boards as db_boards

from nti.analytics.database.users import get_user_db_id
from nti.analytics.database.boards import ForumsCreated
from nti.analytics.database.boards import TopicLikes
from nti.analytics.database.boards import TopicFavorites
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import TopicsViewed
from nti.analytics.database.boards import ForumCommentLikes
from nti.analytics.database.boards import ForumCommentFavorites
from nti.analytics.database.boards import ForumCommentsCreated

from nti.analytics.database.tests import DEFAULT_INTID

class TestForums(AnalyticsTestBase):

	def setUp(self):
		super( TestForums, self ).setUp()
		self.forum_id = 1
		self.forum_ds_id = 999

	def test_forums(self):
		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 0 ) )
		my_forum = MockForum( None, intid=self.forum_ds_id )

		# Pre-emptive delete is ok
		db_boards.delete_forum( datetime.now(), self.forum_ds_id )

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

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_topics(self, mock_validate):
		mock_validate.is_callable().returns( True )
		context_path = None

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 0 ) )

		# Pre-emptive delete is ok
		db_boards.delete_topic( datetime.now(), DEFAULT_INTID )

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
										self.course_id, context_path, my_topic,
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

		# Now our call
		results = db_boards.get_topic_views( test_user_ds_id, my_topic )
		assert_that( results, has_length( 1 ) )

		topic = results[0]
		assert_that( topic.user, is_( test_user_ds_id ) )
		assert_that( topic.RootContext, not_none())
		assert_that( topic.Duration, is_( time_length ) )

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
		context_path = None

		topic_ds_id = DEFAULT_INTID
		my_topic = MockTopic( self.forum, intid=topic_ds_id )
		# Create topic
		db_boards.create_topic( test_user_ds_id,
								test_session_id, self.course_id, my_topic )

		event_time = datetime.now()
		time_length = 30
		new_time_length = time_length + 1
		db_boards.create_topic_view( test_user_ds_id,
										test_session_id, event_time,
										self.course_id, context_path, my_topic,
										time_length )

		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 1 ) )

		db_boards.create_topic_view( test_user_ds_id,
										test_session_id, event_time,
										self.course_id, context_path, my_topic,
										new_time_length )

		results = self.session.query( TopicsViewed ).all()
		assert_that( results, has_length( 1 ) )

		topic_view = results[0]
		assert_that( topic_view.time_length, new_time_length )

	def _do_test_rating(self, table, _rating_call ):
		"For table and rating call, do basic tests."
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

		event_time = datetime.now()
		topic_ds_id = DEFAULT_INTID
		my_topic = MockTopic( self.forum, intid=topic_ds_id )
		# Create topic
		topic_record = db_boards.create_topic( test_user_ds_id,
								test_session_id, self.course_id, my_topic )

		delta = 1
		new_user_ds_id = 111111
		_rating_call( my_topic, new_user_ds_id,
						test_session_id, event_time, delta )

		results = self.session.query( table ).all()
		assert_that( results, has_length( 1 ) )

		rating_record = results[0]
		assert_that( rating_record.user_id, not_none() )
		assert_that( rating_record.session_id, is_( test_session_id ) )
		assert_that( rating_record.topic_id, is_( topic_record.topic_id ) )
		assert_that( rating_record.timestamp, not_none() )
		assert_that( rating_record.creator_id, is_( topic_record.user_id ))
		assert_that( rating_record.course_id, is_( topic_record.course_id ))

		# Now revert
		delta = -1
		_rating_call( my_topic, new_user_ds_id,
					test_session_id, event_time, delta )
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

	def test_likes(self):
		self._do_test_rating( TopicLikes, db_boards.like_topic )

	def test_favorites(self):
		self._do_test_rating( TopicFavorites, db_boards.favorite_topic )

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
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		# Pre-emptive delete is ok
		db_boards.delete_forum_comment( datetime.now(), DEFAULT_INTID )

		# Topic parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )

		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments( course=self.course_id )
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
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )
		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_comment_with_parent(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
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

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments( course=self.course_id )
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
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
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

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 2 ) )

		results = db_boards.get_forum_comments( course=self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 2 ) )

		#Deleted comments not returned
		db_boards.delete_forum_comment( datetime.now(), 20 )

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].Comment, new_comment2 )

		results = db_boards.get_forum_comments( course=self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].Comment, new_comment2 )

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_multiple_comments_users(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
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
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].Comment, new_comment2 )

		results = db_boards.get_forum_comments( course=self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 2 ) )
		results = [x.Comment for x in results]
		assert_that( results, has_items( new_comment1, new_comment2 ) )

	def _do_test_rating(self, table, _rating_call ):
		"For table and rating call, do basic tests."
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

		event_time = datetime.now()
		# Topic parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )

		comment_record = db_boards.create_forum_comment( test_user_ds_id,
										test_session_id, self.course_id,
										self.topic, my_comment )

		delta = 1
		new_user_ds_id = 111111
		_rating_call( my_comment, new_user_ds_id,
						test_session_id, event_time, delta )

		results = self.session.query( table ).all()
		assert_that( results, has_length( 1 ) )

		rating_record = results[0]
		assert_that( rating_record.user_id, not_none() )
		assert_that( rating_record.session_id, is_( test_session_id ) )
		assert_that( rating_record.timestamp, not_none() )
		assert_that( rating_record.creator_id, is_( comment_record.user_id ))
		assert_that( rating_record.course_id, is_( comment_record.course_id ))

		# Now revert
		delta = -1
		_rating_call( my_comment, new_user_ds_id, test_session_id, event_time, delta )
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

	def test_likes(self):
		self._do_test_rating( ForumCommentLikes, db_boards.like_comment )

	def test_favorites(self):
		self._do_test_rating( ForumCommentFavorites, db_boards.favorite_comment )

class TestLazyCreate(AnalyticsTestBase):
	"""
	Validate that board objects can be auto-created.
	"""

	def setUp(self):
		super( TestLazyCreate, self ).setUp()
		self.course_id = 1
		self.forum_id = 1
		self.forum_ds_id = 999
		self.topic_id = 1
		self.topic_ds_id = DEFAULT_INTID
		self.forum = MockForum( None, intid=self.forum_ds_id )
		self.forum.creator = self.forum_creator = Principal( username='1979' )
		self.forum_creator.__dict__['_ds_intid']  = '1979'
		self.topic = MockTopic( self.forum, intid=self.topic_ds_id  )
		self.topic.creator = self.topic_creator = Principal( username='1968' )
		self.topic_creator.__dict__['_ds_intid']  = '1968'

	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_comments(self, mock_validate):
		mock_validate.is_callable().returns( True )
		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 0 ) )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Topic parent
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.topic, intid=comment_id )

		# Will create our forum, topic, and comment: in order.
		db_boards.create_forum_comment( test_user_ds_id, test_session_id, self.course_id,
										self.topic, my_comment )

		results = db_boards.get_forum_comments( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		results = db_boards.get_forum_comments( course=self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		comment_creator_db_id = get_user_db_id( test_user_ds_id )
		forum_creator_db_id = get_user_db_id( self.forum_creator )
		topic_creator_db_id = get_user_db_id( self.topic_creator )

		results = self.session.query( ForumCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].user_id, is_( comment_creator_db_id ) )

		results = self.session.query( ForumsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].user_id, is_( forum_creator_db_id ) )

		results = self.session.query( TopicsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].user_id, is_( topic_creator_db_id ) )
