#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

import zope.intid

from datetime import datetime

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

from nti.analytics.progress import get_topic_progress
from nti.analytics.progress import _get_last_mod_progress
from nti.analytics.progress import get_progress_for_video_views

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.forum import CommunityForum

from nti.testing.time import time_monotonically_increases

from nti.analytics.tests import NTIAnalyticsTestCase


class MockDBRecord( object ):
	"""
	Mock a database record with a few fields.
	"""

	def  __init__(self, timestamp, time_length=None, MaxDuration=None, VideoEndTime=None ):
		self.timestamp = timestamp
		self.time_length = time_length
		self.MaxDuration = MaxDuration
		self.VideoEndTime = VideoEndTime


class TestProgress( TestCase ):

	def test_last_mod_progress(self):
		# Non cases
		result = _get_last_mod_progress(None, 'test')
		assert_that( result, none() )

		result = _get_last_mod_progress([], 'test')
		assert_that( result, none() )

		# Single
		record = MockDBRecord( 1 )
		last_mod = datetime.utcfromtimestamp(1)
		result = _get_last_mod_progress( (record,), 'test')
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_(last_mod))
		assert_that( result.NTIID, is_( 'test' ))

		# Multi
		record2 = MockDBRecord( 10 )
		record3 = MockDBRecord( 0 )
		last_mod = datetime.utcfromtimestamp(10)
		result = _get_last_mod_progress( [record, record2, record3], 'test')
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_(last_mod))
		assert_that( result.LastModified, is_(last_mod))
		assert_that( result.NTIID, is_('test'))

	def test_video_progress(self):
		ntiid = 'ntiid_video'
		# Non cases
		result = get_progress_for_video_views(ntiid, [])
		assert_that( result, none() )
		result = get_progress_for_video_views(ntiid, None)
		assert_that( result, none() )

		# Single
		record = MockDBRecord( timestamp=1 )
		last_mod = datetime.utcfromtimestamp(1)
		records = (record,)
		result = get_progress_for_video_views(ntiid, records)
		assert_that( result.NTIID, is_( ntiid ))
		assert_that( result.AbsoluteProgress, is_( 0 ))
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.LastModified, is_(last_mod))
		assert_that( result.MaxPossibleProgress, none())
		assert_that( result.MostRecentEndTime, none())

		# Multiple
		record2 = MockDBRecord( timestamp=2, time_length=05, MaxDuration=30, VideoEndTime=7 )
		record3 = MockDBRecord( timestamp=3, time_length=0, MaxDuration=None, VideoEndTime=27 )
		record4 = MockDBRecord( timestamp=4, time_length=25, MaxDuration=30, VideoEndTime=17 )
		records = (record, record2, record3, record4)
		result = get_progress_for_video_views(ntiid, records)
		assert_that( result.NTIID, is_( ntiid ))
		assert_that( result.AbsoluteProgress, is_( 30 ))
		assert_that( result.HasProgress, is_( True ))
		assert_that(result.LastModified,
					is_(datetime.utcfromtimestamp(4)))
		assert_that( result.MaxPossibleProgress, is_( 30 ))
		assert_that( result.MostRecentEndTime, is_( 17 ))

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
		assert_that( result.NTIID, is_( self.topic.NTIID ) )
		assert_that( result.last_modified, is_( t1 ) )

		# Some
		t2 = timestamp_type( time.time() )
		self._install_event( t2 )
		t3 = timestamp_type( time.time() )
		self._install_event( t3, time_length=30 )

		result = get_topic_progress( self.user, self.topic )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ) )
		assert_that( result.NTIID, is_( self.topic.NTIID ) )
		assert_that( result.last_modified, is_( t3 ) )
