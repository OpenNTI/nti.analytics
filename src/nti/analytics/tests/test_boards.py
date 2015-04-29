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
from ..boards import get_replies_to_user
from ..boards import get_user_replies_to_others

class TestComments( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_reply_comments(self, mock_find_object):
		user1 = User.create_user( username='new_user1', dataserver=self.ds )
		user2 = User.create_user( username='new_user2', dataserver=self.ds )

		intids = component.getUtility( zope.intid.IIntIds )
		course = CourseInstance()

		# Create forum/topic
		# Should be lazily created in analytics
		forum = GeneralForum()
		forum.creator = user1
		forum.__parent__ = course
		intids.register( forum )

		topic = GeneralTopic()
		topic.creator = user1
		topic.__parent__ = forum
		intids.register( topic )

		# Now our hierarchal comments
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
		comment2.__parent__ = comment1
		intids.register( comment2 )
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
