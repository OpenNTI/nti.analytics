#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import fudge
import zope.intid

from zope import component

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from zope.file.file import File

from nti.dataserver.users import User

from nti.dataserver.contenttypes.canvas import Canvas
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasUrlShape

from nti.dataserver.contenttypes.forums.forum import PersonalBlog

from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry

from nti.dataserver.contenttypes.forums.post import PersonalBlogComment
from nti.dataserver.contenttypes.forums.post import PersonalBlogEntryPost

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.namedfile.file import NamedBlobFile

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.blogs import get_blogs
from nti.analytics.blogs import _add_blog
from nti.analytics.blogs import _add_comment
from nti.analytics.blogs import _like_blog
from nti.analytics.blogs import _favorite_blog
from nti.analytics.blogs import _like_comment
from nti.analytics.blogs import _favorite_comment
from nti.analytics.blogs import get_blog_comments
from nti.analytics.blogs import get_replies_to_user
from nti.analytics.blogs import get_user_replies_to_others
from nti.analytics.blogs import get_likes_for_users_blogs
from nti.analytics.blogs import get_likes_for_users_comments
from nti.analytics.blogs import get_favorites_for_users_blogs
from nti.analytics.blogs import get_favorites_for_users_comments

class TestBlogs( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_add_blogs(self, mock_find_object):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		results = get_blogs( user )
		assert_that( results, has_length( 0 ))

		blog_container = PersonalBlog()

		blog = PersonalBlogEntry()
		blog._ds_intid = 888
		blog.creator = user
		blog.headline = PersonalBlogEntryPost()
		blog.__parent__ = blog_container
		mock_find_object.is_callable().returns( blog )
		oid = 13

		_add_blog( oid )

		results = get_blogs( user )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Blog, is_( blog ))
		assert_that( results[0].user, is_( user ))
		assert_that( results[0].BlogLength, is_( 0 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_reply_comments(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		intids = component.getUtility( zope.intid.IIntIds )

		# Create blog/comment
		blog = PersonalBlogEntry()
		blog._ds_intid = 888
		blog.creator = user1
		mock_find_object.is_callable().returns( blog )
		oid = 13

		_add_blog( oid )

		comment1 = PersonalBlogComment()
		comment1.creator = user2
		comment1.__parent__ = blog
		intids.register( comment1 )
		mock_find_object.is_callable().returns( comment1 )

		_add_comment( comment1 )

		results = get_replies_to_user( user2 )
		assert_that( results, has_length( 0 ))
		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 0 ))
		results = get_blog_comments( user2 )
		assert_that( results, has_length( 1 ))

		# Reply-to
		comment2 = PersonalBlogComment()
		comment2._ds_intid = 9992
		comment2.creator = user1
		comment2.inReplyTo = comment1
		comment2.__parent__ = blog
		mock_find_object.is_callable().returns( comment2 )

		_add_comment( comment2 )

		# Both should return same record
		# Replies to user; User replies to others
		results = get_replies_to_user( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment2 ))
		assert_that( results[0].user, is_( user1 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].CommentLength, is_( 0 ))
		assert_that( results[0].RepliedToUser, is_( user2 ))

		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment2 ))
		assert_that( results[0].user, is_( user1 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].CommentLength, is_( 0 ))
		assert_that( results[0].RepliedToUser, is_( user2 ))

		# Test get comments
		results = get_blog_comments( user2 )
		assert_that( results, has_length( 1 ))
		results = get_blog_comments( user1 )
		assert_that( results, has_length( 1 ))

		# The reverse is nothing
		results = get_replies_to_user( user1 )
		assert_that( results, has_length( 0 ))
		results = get_user_replies_to_others( user2 )
		assert_that( results, has_length( 0 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_rated_blogs_and_comments(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		intids = component.getUtility( zope.intid.IIntIds )

		# Create blog/comment
		blog = PersonalBlogEntry()
		blog._ds_intid = 888
		blog.creator = user1
		mock_find_object.is_callable().returns( blog )
		oid = 13

		_add_blog( oid )

		comment1 = PersonalBlogComment()
		comment1.creator = user2
		comment1.__parent__ = blog
		intids.register( comment1 )
		mock_find_object.is_callable().returns( comment1 )

		_add_comment( comment1 )

		# Base
		results = get_likes_for_users_blogs( user1 )
		assert_that( results, has_length( 0 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_blogs( user1 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Like blog
		mock_find_object.is_callable().returns( blog )
		_like_blog( 11, delta=1, username=user2.username )

		results = get_likes_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_blogs( user1 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Favorite blog
		mock_find_object.is_callable().returns( blog )
		_favorite_blog( 11, delta=1, username=user2.username )

		results = get_likes_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Like comment
		mock_find_object.is_callable().returns( comment1 )
		_like_comment( 11, delta=1, username=user1.username )

		results = get_likes_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Favorite comment
		mock_find_object.is_callable().returns( comment1 )
		_favorite_comment( 11, delta=1, username=user1.username )

		results = get_likes_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 1 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_blog_user_files(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		results = get_blogs( user1 )
		assert_that( results, has_length( 0 ))
		results = get_blog_comments( user1 )
		assert_that( results, has_length( 0 ))

		# Create blog/comment without files; post is created automatically.
		blog = PersonalBlogEntry()
		blog._ds_intid = 888
		blog.creator = user1
		mock_find_object.is_callable().returns( blog )
		oid = 13

		comment = PersonalBlogEntryPost()
		comment._ds_intid = 9992
		comment.creator = user1
		comment.inReplyTo = None
		comment.__parent__ = blog
		blog.headline = comment
		_add_blog( oid )

		results = get_blogs( user1 )
		assert_that( results, has_length( 1 ))
		results = get_blog_comments( user1 )
		assert_that( results, has_length( 1 ))
		comment_record = results[0]
		assert_that( comment_record.FileMimeTypes, has_length( 0 ))

		# Create blog/comment with headline post with files
		blog._ds_intid = 999
		comment._ds_intid = 9999
		comment.creator = blog.creator = user2

		text_file = NamedBlobFile(data='data', contentType=b'text/plain', filename='foo.txt')
		image_file = NamedBlobFile(data='data', contentType=b'image/gif', filename='foo.jpg')
		canvas = Canvas()
		url_shape = NonpersistentCanvasUrlShape()
		url_shape._file = File( 'image/png' )
		canvas.shapeList = (object(), url_shape,)
		text_length = len( 'text_length' )
		comment.body = ('text_length', text_file, text_file, image_file, 'text_length', canvas)

		_add_blog( oid )
		results = get_blog_comments( user2 )
		assert_that( results, has_length( 1 ))
		comment_record = results[0]
		assert_that( comment_record.comment_length, is_( text_length * 2 ))
		assert_that( comment_record.FileMimeTypes, has_length( 3 ))
		assert_that( comment_record.FileMimeTypes.get( 'text/plain' ), is_( 2 ))
		assert_that( comment_record.FileMimeTypes.get( 'image/gif' ), is_( 1 ))
		assert_that( comment_record.FileMimeTypes.get( 'image/png' ), is_( 1 ))
