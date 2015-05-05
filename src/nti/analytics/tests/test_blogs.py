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

from nti.dataserver.users import User

from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry
from nti.dataserver.contenttypes.forums.post import PersonalBlogComment

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..blogs import get_blogs
from ..blogs import _add_blog
from ..blogs import _add_comment
from ..blogs import _like_blog
from ..blogs import _favorite_blog
from ..blogs import _like_comment
from ..blogs import _favorite_comment
from ..blogs import get_replies_to_user
from ..blogs import get_user_replies_to_others
from ..blogs import get_likes_for_users_blogs
from ..blogs import get_likes_for_users_comments
from ..blogs import get_favorites_for_users_blogs
from ..blogs import get_favorites_for_users_comments

class TestBlogs( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_add_blogs(self, mock_find_object):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		results = get_blogs( user )
		assert_that( results, has_length( 0 ))

		blog = PersonalBlogEntry()
		blog._ds_intid = 888
		blog.creator = user
		mock_find_object.is_callable().returns( blog )
		oid = 13

		_add_blog( oid )

		results = get_blogs( user )
		assert_that( results, has_length( 1 ))

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

		# Reply-to
		comment2 = PersonalBlogComment()
		comment2._ds_intid = 9992
		comment2.creator = user1
		comment2.inReplyTo = comment1
		comment2.__parent__ = comment1
		mock_find_object.is_callable().returns( comment2 )

		_add_comment( comment2 )

		# Both should return same record
		# Replies to user; User replies to others
		results = get_replies_to_user( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].comment_id, is_( comment2._ds_intid ))

		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].comment_id, is_( comment2._ds_intid ))

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
