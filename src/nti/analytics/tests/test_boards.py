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

from datetime import datetime
from datetime import timedelta

from zope import component

from zope.file.file import File

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User
from nti.dataserver.users import Community

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.contenttypes.canvas import Canvas
from nti.dataserver.contenttypes.canvas import NonpersistentCanvasUrlShape

from nti.dataserver.contenttypes.forums.forum import GeneralForum

from nti.dataserver.contenttypes.forums.topic import GeneralTopic
from nti.dataserver.contenttypes.forums.topic import GeneralHeadlineTopic

from nti.dataserver.contenttypes.forums.post import GeneralForumComment
from nti.dataserver.contenttypes.forums.post import GeneralHeadlinePost

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.namedfile.file import NamedBlobFile

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.boards import _add_comment
from nti.analytics.boards import _update_comment
from nti.analytics.boards import _like_topic
from nti.analytics.boards import _like_comment
from nti.analytics.boards import _favorite_topic
from nti.analytics.boards import _favorite_comment
from nti.analytics.boards import _add_topic
from nti.analytics.boards import _update_topic
from nti.analytics.boards import get_topic_views
from nti.analytics.boards import get_replies_to_user
from nti.analytics.boards import get_forum_comments
from nti.analytics.boards import get_topics_created_for_user
from nti.analytics.boards import get_user_replies_to_others
from nti.analytics.boards import get_likes_for_users_topics
from nti.analytics.boards import get_forum_comments_for_user
from nti.analytics.boards import get_likes_for_users_comments
from nti.analytics.boards import get_favorites_for_users_topics
from nti.analytics.boards import get_favorites_for_users_comments

from nti.analytics.model import TopicViewEvent

from nti.analytics.resource_views import _add_topic_event

class TestComments( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.analytics.boards.find_object_with_ntiid' )
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

		results = get_forum_comments( user2 )
		assert_that( results, has_length( 1 ))
		results = get_forum_comments( course=course )
		assert_that( results, has_length( 1 ))
		results = get_forum_comments( course=course, replies_only=True )
		assert_that( results, has_length( 0 ))
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
		assert_that( results[0].RepliedToUser, is_( user2 ))

		results = get_user_replies_to_others( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment2 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user1 ))

		results = get_forum_comments( course=course, replies_only=True )
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

		# Topic filter
		results = get_user_replies_to_others( user1, topic=topic )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Comment, is_( comment2 ))
		assert_that( results[0].IsReply, is_( True ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user1 ))
		assert_that( results[0].RepliedToUser, is_( user2 ))

		# Topic filtered out
		results = get_user_replies_to_others( user1, topic=GeneralTopic() )
		assert_that( results, has_length( 0 ))

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
	@fudge.patch( 'nti.analytics.boards.find_object_with_ntiid' )
	def test_rated_topics_and_comments(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		intids = component.getUtility( zope.intid.IIntIds )
		course = CourseInstance()

		# Create forum/topic; should be lazily created
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

	@WithMockDSTrans
	@fudge.patch( 'nti.analytics.boards.find_object_with_ntiid' )
	@fudge.patch( 'nti.analytics.resource_views.find_object_with_ntiid' )
	@fudge.patch( 'nti.analytics.resource_views._get_root_context' )
	def test_topics(self, mock_find_object_boards, mock_find_object, mock_root_context):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		intids = component.getUtility( zope.intid.IIntIds )
		course = CourseInstance()
		course._ds_intid = 123456
		mock_root_context.is_callable().returns( course )

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

		# Base
		results = get_topic_views( user1 )
		assert_that( results, has_length( 0 ))

		# One View
		time_length = 30
		event = TopicViewEvent()
		event.topic_id = 'tag:nextthought.com,2011-10:topic_ntiid'
		event.RootContextID = 'tag:nextthought.com,2011-10:course_ntiid'
		event.timestamp = now = datetime.utcnow()
		now = now.replace( microsecond=0 )
		event.user = user1.username
		event.Duration = time_length
		mock_find_object.is_callable().returns(topic)
		mock_find_object_boards.is_callable().returns(topic)
		_add_topic_event( event )

		results = get_topic_views( user1 )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].Topic, is_( topic ))
		assert_that( results[0].user, is_( user1 ))
		#Need to fake return course...
		#assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].timestamp, is_( now ) )

		# Query with topic_id
		results = get_topic_views( user1, topic )
		assert_that( results, has_length( 1 ))

		results = get_topic_views( user1, event.topic_id + 'xxx' )
		assert_that( results, has_length( 0 ))

		# View topic on entity stream
		community = Community.create_community( username='community_name' )
		mock_root_context.is_callable().returns( community )
		event.timestamp = now + timedelta( minutes=5 )
		mock_find_object.is_callable().returns(topic)
		mock_find_object_boards.is_callable().returns(topic)
		_add_topic_event( event )

		results = get_topic_views( user1 )
		assert_that( results, has_length( 2 ))

		results = get_topic_views( user1, course=course )
		assert_that( results, has_length( 1 ))

		# A topic created on entity
		user2 = User.create_user( username='new_user2', dataserver=self.ds )
		forum = GeneralForum()
		forum.creator = user2
		intids.register( forum )

		topic = GeneralTopic()
		topic.creator = user2
		topic.__parent__ = forum
		intids.register( topic )
		forum.__parent__ = community
		mock_find_object.is_callable().returns( topic )
		mock_find_object_boards.is_callable().returns(topic)
		_add_topic( topic )
		topics = get_topics_created_for_user( user2 )
		assert_that( topics, has_length( 1 ))
		assert_that( topics[0].RootContext, is_( community ))

	@WithMockDSTrans
	@fudge.patch( 'nti.analytics.boards.find_object_with_ntiid' )
	def test_topic_user_files(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		results = get_topics_created_for_user( user1 )
		assert_that( results, has_length( 0 ))
		results = get_forum_comments_for_user( user1 )
		assert_that( results, has_length( 0 ))

		# Create topic/comment without files; post is created automatically.
		topic = GeneralHeadlineTopic()
		topic._ds_intid = 888
		topic.creator = user1
		mock_find_object.is_callable().returns( topic )
		oid = 13

		comment = GeneralHeadlinePost()
		comment._ds_intid = 9992
		comment.creator = user1
		comment.inReplyTo = None
		comment.__parent__ = topic
		topic.headline = comment
		_add_topic( oid )

		results = get_topics_created_for_user( user1 )
		assert_that( results, has_length( 1 ))
		results = get_forum_comments_for_user( user1 )
		assert_that( results, has_length( 1 ))
		comment_record = results[0]
		assert_that( comment_record.FileMimeTypes, has_length( 0 ))

		# Create topic/comment with headline post with files
		topic._ds_intid = 999
		comment._ds_intid = 9999
		comment.creator = topic.creator = user2

		text_file = NamedBlobFile(data='data', contentType=b'text/plain', filename='foo.txt')
		image_file = NamedBlobFile(data='data', contentType=b'image/gif', filename='foo.jpg')
		canvas = Canvas()
		url_shape = NonpersistentCanvasUrlShape()
		url_shape._file = File( 'image/png' )
		canvas.shapeList = (object(), url_shape,)
		text_length = len( 'text_length' )
		comment.body = ('text_length', text_file, text_file, image_file, 'text_length', canvas)

		_add_topic( oid )
		results = get_forum_comments_for_user( user2 )
		assert_that( results, has_length( 1 ))
		comment_record = results[0]
		assert_that( comment_record.comment_length, is_( text_length * 2 ))
		assert_that( comment_record.FileMimeTypes, has_length( 3 ))
		assert_that( comment_record.FileMimeTypes.get( 'text/plain' ), is_( 2 ))
		assert_that( comment_record.FileMimeTypes.get( 'image/gif' ), is_( 1 ))
		assert_that( comment_record.FileMimeTypes.get( 'image/png' ), is_( 1 ))

		# Update topic
		mock_find_object.is_callable().returns( topic )
		_update_topic( topic )
		results = get_topics_created_for_user( user1 )
		assert_that( results, has_length( 1 ))

		# Update comment
		comment.body = ( 'a', )
		mock_find_object.is_callable().returns( comment )
		_update_comment( oid )
		results = get_forum_comments_for_user( user2 )
		assert_that( results, has_length( 1 ))
		comment_record = results[0]
		assert_that( comment_record.comment_length, is_( 1 ))
		assert_that( comment_record.FileMimeTypes, has_length( 0 ))
