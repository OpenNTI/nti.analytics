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

from nti.dataserver.contenttypes.forums.post import CommentPost

from nti.dataserver.users.users import Principal

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import blogs as db_blogs

from nti.analytics.database.blogs import BlogLikes
from nti.analytics.database.blogs import BlogFavorites
from nti.analytics.database.blogs import BlogsCreated
from nti.analytics.database.blogs import BlogsViewed
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.blogs import BlogCommentLikes
from nti.analytics.database.blogs import BlogCommentFavorites

from nti.analytics.database.users import get_user_db_id

# For new objects, this is the default intid stored in the database.
# For subsequent objects, this will increase by one.
from nti.analytics.database.tests import DEFAULT_INTID

class TestBlog(AnalyticsTestBase):

	def setUp(self):
		super( TestBlog, self ).setUp()

	def test_create_blog(self):
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 0 ) )
		context_path = None

		# Pre-emptive delete is ok
		db_blogs.delete_blog( datetime.now(), 999 )

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

		db_blogs.create_blog_view( test_user_ds_id, test_session_id, datetime.now(), context_path, new_blog, 18 )
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

	def test_idempotent(self):
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 0 ) )

		new_blog_ds_id = 999
		new_blog = MockParent( None, intid=new_blog_ds_id )
		db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )

		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )

		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 1 ) )

	def test_idempotent_views(self):
		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 0 ) )
		context_path = None

		time_length = 18
		new_time_length = time_length + 1

		event_time = datetime.now()
		new_blog_ds_id = 999
		new_blog = MockParent( None, intid=new_blog_ds_id )
		db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )
		db_blogs.create_blog_view( test_user_ds_id, test_session_id, event_time, context_path, new_blog, time_length )

		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )

		db_blogs.create_blog_view( test_user_ds_id, test_session_id, event_time, context_path, new_blog, new_time_length )

		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )

		blog_view = results[0]
		assert_that( blog_view.time_length, is_( new_time_length ) )

	def _do_test_rating(self, table, _rating_call ):
		"For table and rating call, do basic tests."
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

		event_time = datetime.now()
		new_blog_ds_id = 999
		new_blog = MockParent( None, intid=new_blog_ds_id )
		new_blog_record = db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )

		delta = 1
		new_user_ds_id = 111111
		_rating_call( new_blog_ds_id, new_user_ds_id,
						test_session_id, event_time, delta )

		results = self.session.query( table ).all()
		assert_that( results, has_length( 1 ) )

		rating_record = results[0]
		assert_that( rating_record.user_id, not_none() )
		assert_that( rating_record.session_id, is_( test_session_id ) )
		assert_that( rating_record.blog_id, is_( new_blog_record.blog_id ) )
		assert_that( rating_record.timestamp, not_none() )
		assert_that( rating_record.creator_id, is_( new_blog_record.user_id ))

		# Now revert
		delta = -1
		_rating_call( new_blog, new_user_ds_id, test_session_id, event_time, delta )
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

	def test_likes(self):
		self._do_test_rating( BlogLikes, db_blogs.like_blog )

	def test_favorites(self):
		self._do_test_rating( BlogFavorites, db_blogs.favorite_blog )

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

	def test_idempotent(self):
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		comment_id = DEFAULT_INTID
		my_comment = MockComment( MockThought( None ), intid=comment_id )
		db_blogs.create_blog_comment( test_user_ds_id, test_session_id, self.blog_ds_id, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		db_blogs.create_blog_comment( test_user_ds_id, test_session_id, self.blog_ds_id, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

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

	def _do_test_rating(self, table, _rating_call ):
		"For table and rating call, do basic tests."
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

		event_time = datetime.now()
		comment_id = DEFAULT_INTID
		my_comment = MockComment( CommentPost(), inReplyTo=CommentPost(), intid=comment_id )
		comment_record = db_blogs.create_blog_comment( test_user_ds_id, test_session_id,
													self.blog_ds_id, my_comment )

		delta = 1
		new_user_ds_id = 111111
		_rating_call( comment_id, new_user_ds_id,
						test_session_id, event_time, delta )

		results = self.session.query( table ).all()
		assert_that( results, has_length( 1 ) )

		rating_record = results[0]
		assert_that( rating_record.user_id, not_none() )
		assert_that( rating_record.session_id, is_( test_session_id ) )
		assert_that( rating_record.comment_id, is_( comment_record.comment_id ) )
		assert_that( rating_record.timestamp, not_none() )
		assert_that( rating_record.creator_id, is_( comment_record.user_id ))

		# Now revert
		delta = -1
		_rating_call( comment_id, new_user_ds_id, test_session_id, event_time, delta )
		results = self.session.query( table ).all()
		assert_that( results, has_length( 0 ) )

	def test_likes(self):
		self._do_test_rating( BlogCommentLikes, db_blogs.like_comment )

	def test_favorites(self):
		self._do_test_rating( BlogCommentFavorites, db_blogs.favorite_comment )

class TestBlogLazyCreate(AnalyticsTestBase):
	"""
	Blog comments and views will auto create blog.
	"""

	def setUp(self):
		super( TestBlogLazyCreate, self ).setUp()
		self.blog_ds_id = 999
		self.blog_id = 1
		self.new_blog = MockParent( None, intid=self.blog_ds_id )
		self.blog_creator = Principal( username=str( test_user_ds_id ) )
		self.blog_creator.__dict__['_ds_intid'] = test_user_ds_id
		self.new_blog.creator = self.blog_creator

	def tearDown(self):
		self.session.close()

	def test_comments(self):
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 0 ) )

		# Create comment
		comment_id = DEFAULT_INTID
		my_comment = MockComment( self.new_blog, intid=comment_id )
		db_blogs.create_blog_comment( '9999', test_session_id, self.new_blog, my_comment )

		results = self.session.query( BlogCommentsCreated ).all()
		assert_that( results, has_length( 1 ) )

		blog_creator_db_id = get_user_db_id( self.blog_creator )

		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].user_id, is_( blog_creator_db_id ))

	def test_views(self):
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 0 ) )
		context_path = None

		# Create blog
		db_blogs.create_blog_view( '9999', test_session_id, datetime.now(), context_path, self.new_blog, 18 )

		blog_creator_db_id = get_user_db_id( self.blog_creator )

		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )
		results = self.session.query( BlogsCreated ).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].user_id, is_( blog_creator_db_id ))
