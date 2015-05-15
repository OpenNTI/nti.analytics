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

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.contenttypes.forums.forum import GeneralForum
from nti.dataserver.contenttypes.forums.topic import GeneralTopic
from nti.dataserver.contenttypes.forums.post import GeneralForumComment

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..boards import _add_comment
from ..boards import _like_topic
from ..boards import _like_comment
from ..boards import _favorite_topic
from ..boards import _favorite_comment
from ..boards import get_replies_to_user
from ..boards import get_user_replies_to_others
from ..boards import get_likes_for_users_topics
from ..boards import get_forum_comments_for_user
from ..boards import get_likes_for_users_comments
from ..boards import get_favorites_for_users_topics
from ..boards import get_favorites_for_users_comments

class TestComments( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_reply_comments(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		intids = component.getUtility( zope.intid.IIntIds )
		course = CourseInstance()
		course._ds_intid = 123456

		# Create forum/topic
		# Should be lazily created
		forum = GeneralForum()
		forum.creator = user1
		forum.NTIID = 'tag:nextthought.com,2011-10:imaforum'
		forum.__parent__ = course
		intids.register( forum )

		topic = GeneralTopic()
		topic.creator = user1
		topic.NTIID = 'tag:nextthought.com,2011-10:imatopic'
		topic.__parent__ = forum
		intids.register( topic )

		# Now our hierarchical comments
		comment1 = GeneralForumComment()
		comment1.creator = user2
		comment1.body = ('test222',)
		comment1.__parent__ = topic
		intids.register( comment1 )
		mock_find_object.is_callable().returns( comment1 )
		_add_comment( comment1 )

		results = get_replies_to_user( user2 )
		assert_that( results, has_length( 0 ))
		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 0 ))

		# Reply-to
		comment2 = GeneralForumComment()
		comment2.creator = user1
		comment2.body = ('test222',)
		comment2.inReplyTo = comment1
		comment2.__parent__ = topic
		intids.register( comment2 )
		mock_find_object.is_callable().returns( comment2 )
		_add_comment( comment2 )

		# Both should return same record
		# Replies to user; User replies to others
		results = get_replies_to_user( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment2 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user1 ))

		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment2 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user1 ))

		# The reverse is nothing
		results = get_replies_to_user( user1 )
		assert_that( results, has_length( 0 ))
		results = get_user_replies_to_others( user2 )
		assert_that( results, has_length( 0 ))

		# Basic fetch
		results = get_forum_comments_for_user( user2 )
		assert_that( results[0].Comment, is_( comment1 ))
		assert_that( results[0].IsReply, is_( False ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user2 ))

		# Course filter
		results = get_forum_comments_for_user( user2, course )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment1 ))
		assert_that( results[0].IsReply, is_( False ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user2 ))

		# Course filtered out
		course2 = CourseInstance()
		course2._ds_intid = 7891011
		results = get_forum_comments_for_user( user2, course2 )
		assert_that( results, has_length( 0 ))

		# Top level
		results = get_forum_comments_for_user( user2, course, top_level_only=True )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment1 ))
		assert_that( results[0].IsReply, is_( False ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user2 ))

		# Not top level
		results = get_forum_comments_for_user( user1, course, top_level_only=True )
		assert_that( results, has_length( 0 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_rated_topics_and_comments(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		intids = component.getUtility( zope.intid.IIntIds )
		course = CourseInstance()

		# Create forum/topic
		# Should be lazily created
		forum = GeneralForum()
		forum.creator = user1
		forum.__parent__ = course
		intids.register( forum )

		topic = GeneralTopic()
		topic.creator = user1
		topic.__parent__ = forum
		intids.register( topic )

		comment1 = GeneralForumComment()
		comment1.creator = user2
		comment1.body = ('test222',)
		comment1.__parent__ = topic
		intids.register( comment1 )
		mock_find_object.is_callable().returns( comment1 )
		_add_comment( comment1 )

		# Base
		results = get_likes_for_users_topics( user1 )
		assert_that( results, has_length( 0 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_topics( user1 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Like topic
		mock_find_object.is_callable().returns( topic )
		_like_topic( 11, delta=1, username=user2.username )

		results = get_likes_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].ObjectCreator, is_( user1 ))
		assert_that( results[0].user, is_( user2 ))

		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_topics( user1 )
		assert_that( results, has_length( 0 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Favorite topic
		mock_find_object.is_callable().returns( topic )
		_favorite_topic( 11, delta=1, username=user2.username )

		results = get_likes_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))

		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		results = get_favorites_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].ObjectCreator, is_( user1 ))
		assert_that( results[0].user, is_( user2 ))

		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Like comment
		mock_find_object.is_callable().returns( comment1 )
		_like_comment( 11, delta=1, username=user1.username )

		results = get_likes_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))

		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].ObjectCreator, is_( user2 ))
		assert_that( results[0].user, is_( user1 ))

		results = get_favorites_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 0 ))

		# Favorite comment
		mock_find_object.is_callable().returns( comment1 )
		_favorite_comment( 11, delta=1, username=user1.username )

		results = get_likes_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))
		results = get_likes_for_users_comments( user2 )
		assert_that( results, has_length( 1 ))
		results = get_favorites_for_users_topics( user1 )
		assert_that( results, has_length( 1 ))

		results = get_favorites_for_users_comments( user2 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].ObjectCreator, is_( user2 ))
		assert_that( results[0].user, is_( user1 ))
