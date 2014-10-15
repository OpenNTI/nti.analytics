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

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import blogs as db_blogs

from nti.analytics.database.blogs import BlogsCreated
from nti.analytics.database.blogs import BlogsViewed
from nti.analytics.database.blogs import BlogCommentsCreated

# For new objects, this is the default intid stored in the database.
# For subsequent objects, this will increase by one.
from . import DEFAULT_INTID

class TestBlog(AnalyticsTestBase):

	def setUp(self):
		super( TestBlog, self ).setUp()

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

		event_time = datetime.now()
		new_blog_ds_id = 999
		new_blog = MockParent( None, intid=new_blog_ds_id )
		db_blogs.create_blog( test_user_ds_id, test_session_id, new_blog )
		db_blogs.create_blog_view( test_user_ds_id, test_session_id, event_time, new_blog, 18 )

		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )

		db_blogs.create_blog_view( test_user_ds_id, test_session_id, event_time, new_blog, 18 )

		results = self.session.query( BlogsViewed ).all()
		assert_that( results, has_length( 1 ) )

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
