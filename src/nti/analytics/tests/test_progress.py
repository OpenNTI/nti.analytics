#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time
import fudge
import zope.intid

from zope import component

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import none
from hamcrest import not_none

from unittest import TestCase

from nti.analytics.common import timestamp_type

from nti.analytics.database.boards import create_topic_view
from nti.analytics.database.boards import create_topic
from nti.analytics.database.users import create_user
from nti.analytics.database import resource_views as db_views

from nti.analytics.progress import _get_last_mod_progress
from nti.analytics.progress import get_topic_progress
from nti.analytics.resource_views import get_progress_for_ntiid

from nti.contentlibrary.contentunit import ContentUnit
from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.forum import CommunityForum

from nti.testing.time import time_monotonically_increases

from nti.analytics.tests import NTIAnalyticsTestCase

class MockDBRecord( object ):
	"""
	Mock a database record with a few fields.
	"""

	def  __init__(self, timestamp, time_length=None, MaxDuration=None ):
		self.timestamp = timestamp
		self.time_length = time_length
		self.MaxDuration = MaxDuration

class TestProgress( TestCase ):

	def test_last_mod_progress(self):
		# Non cases
		result = _get_last_mod_progress(None, 'test')
		assert_that( result, none() )

		result = _get_last_mod_progress([], 'test')
		assert_that( result, none() )

		# Single
		record = MockDBRecord( 1 )
		result = _get_last_mod_progress( (record,), 'test')
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_( 1 ))
		assert_that( result.ResourceID, is_( 'test' ))

		# Multi
		record2 = MockDBRecord( 10 )
		record3 = MockDBRecord( 0 )
		result = _get_last_mod_progress( [record, record2, record3], 'test')
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_( 10 ))
		assert_that( result.LastModified, is_( 10 ))
		assert_that( result.ResourceID, is_( 'test' ))

class TestTopicProgress( NTIAnalyticsTestCase ):

	def setUp(self):
		super( TestTopicProgress, self ).setUp()

	def _install_user(self):
		self.user = 1
		self.user_id = create_user( self.user ).user_id
		return self.user

	def _install_course(self):
		intids = component.getUtility( zope.intid.IIntIds )
		self.course = new_course = CourseInstance()
		intids.register( new_course )
		return new_course

	def _install_topic(self):
		forum = CommunityForum()
		forum.creator = self.user
		forum.NTIID = 'tag:nextthought.com,2011-10:imaforum'
		forum.__parent__ = self.course
		intids = component.getUtility( zope.intid.IIntIds )
		intids.register( forum )

		self.topic = CommunityHeadlineTopic()
		self.topic.NTIID = 'tag:ntiid1'
		self.topic.__parent__ = forum
		intids.register( self.topic )
		create_topic( self.user, None, self.topic)

	def _install_event(self, timestamp, time_length=None):
		create_topic_view(self.user, None, timestamp, self.course, None, self.topic, time_length)

	@WithMockDSTrans
	@time_monotonically_increases
	def test_topic_progress(self):
		self._install_course()
		self._install_user()
		self._install_topic()

		# Nothing
		result = get_topic_progress( self.user, self.topic )
		assert_that( result, none() )

		# One
		t1 = timestamp_type( time.time() )
		self._install_event( t1 )
		result = get_topic_progress( self.user, self.topic )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ) )
		assert_that( result.ResourceID, is_( self.topic.NTIID ) )
		assert_that( result.last_modified, is_( t1 ) )

		# Some
		t2 = timestamp_type( time.time() )
		self._install_event( t2 )
		t3 = timestamp_type( time.time() )
		self._install_event( t3, time_length=30 )

		result = get_topic_progress( self.user, self.topic )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ) )
		assert_that( result.ResourceID, is_( self.topic.NTIID ) )
		assert_that( result.last_modified, is_( t3 ) )

class TestPagedProgress( NTIAnalyticsTestCase ):

	def _create_resource_view(self, user, resource_val, course):
		time_length = 30
		event_time = time.time()
		db_views.create_course_resource_view( user,
											None, event_time,
											course, None,
											resource_val, time_length )

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_paged_progress(self, mock_find_object):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		course = CourseInstance()

		container = ContentUnit()
		container.NTIID = container_ntiid = 'tag:nextthought.com,2011:bleh'
		mock_find_object.is_callable().returns( container )

		# No children
		result = get_progress_for_ntiid( user, container_ntiid )
		assert_that( result, none() )

		# One child with no views
		child1 = ContentUnit()
		child1.ntiid = child_ntiid = 'tag:nextthought.com,2011:bleh.page_1'
		container.children = children = (child1,)
		# Max progress is different, currently.  Since the container
		# counts towards progress.  This may change.
		max_progress = len( children ) + 1

		mock_find_object.is_callable().returns( container )
		result = get_progress_for_ntiid( user, container_ntiid )
		assert_that( result, none() )

		# Child with view
		self._create_resource_view( user, child_ntiid, course )

		mock_find_object.is_callable().returns( container )
		result = get_progress_for_ntiid( user, container_ntiid )
		assert_that( result, not_none() )
		assert_that( result.AbsoluteProgress, is_( 1 ))
		assert_that( result.MaxPossibleProgress, is_( max_progress ))

		# Multiple children
		child2 = ContentUnit()
		child3 = ContentUnit()
		child2.ntiid = child_ntiid2 = 'tag:nextthought.com,2011:bleh.page_2'
		child3.ntiid = 'tag:nextthought.com,2011:bleh.page_3'
		container.children = children = ( child1, child2, child3 )
		max_progress = len( children ) + 1

		mock_find_object.is_callable().returns( container )
		result = get_progress_for_ntiid( user, container_ntiid )
		assert_that( result, not_none() )
		assert_that( result.AbsoluteProgress, is_( 1 ))
		assert_that( result.MaxPossibleProgress, is_( max_progress ))

		# Original child again
		self._create_resource_view( user, child_ntiid, course )

		mock_find_object.is_callable().returns( container )
		result = get_progress_for_ntiid( user, container_ntiid )
		assert_that( result, not_none() )
		assert_that( result.AbsoluteProgress, is_( 1 ))
		assert_that( result.MaxPossibleProgress, is_( max_progress ))

		# Different child
		self._create_resource_view( user, child_ntiid2, course )

		mock_find_object.is_callable().returns( container )
		result = get_progress_for_ntiid( user, container_ntiid )
		assert_that( result, not_none() )
		assert_that( result.AbsoluteProgress, is_( 2 ))
		assert_that( result.MaxPossibleProgress, is_( max_progress ))
		assert_that( result.HasProgress, is_( True ))
