#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from datetime import datetime

import time

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import none

from unittest import TestCase

from nti.analytics.tests import AnalyticsTestBase

from nti.analytics.tests.test_resource_views import create_video_event

from nti.testing.time import time_monotonically_increases

from nti.analytics.progress import _compute_watched_seconds
from nti.analytics.progress import _get_last_mod_progress
from nti.analytics.progress import get_progress_for_video_views

from nti.contenttypes.completion.tests.test_models import MockUser
from nti.contenttypes.completion.tests.test_models import MockCompletableItem
from nti.contenttypes.completion.tests.test_models import MockCompletionContext



class MockDBRecord( object ):
	"""
	Mock a database record with a few fields.
	"""

	def  __init__(self, timestamp, time_length=None, MaxDuration=None, VideoEndTime=None ):
		self.timestamp = timestamp
		self.time_length = time_length
		self.MaxDuration = MaxDuration
		self.VideoEndTime = VideoEndTime


class TestProgress( AnalyticsTestBase ):

	def test_compute_watched_seconds(self):

		# No segments is 0 time watched
		watched = _compute_watched_seconds([])
		assert_that(watched, is_(0))

		# Simple single segment
		segments = [(0, 100)]
		watched = _compute_watched_seconds(segments)
		assert_that(watched, is_(101)) # 101 not 100 because inclusivity of both ends of the segments
	
		segments = [(20, 50)]
		watched = _compute_watched_seconds(segments)
		assert_that(watched, is_(31))

		segments = [(0, 10), (20, 100)]
		assert_that(_compute_watched_seconds(segments), is_(92))

		segments = [(0, 10), (0, 20), (15, 70), (15, 60), (20, 100)]
		watched = _compute_watched_seconds(segments)
		assert_that(watched, is_(101)) # 101 not 100 because inclusivity of both ends of the segments

	def test_jacked_segments(self):
		segments = [(0, 10), (20, 100), (80000, 100)]
		assert_that(_compute_watched_seconds(segments), is_(92))
		

	def test_last_mod_progress(self):
		user = MockUser(u'test_user')
		item = MockCompletableItem(u'ntiid')
		context = MockCompletionContext()
		# Non cases
		result = _get_last_mod_progress(None, 'test', item, user, context)
		assert_that( result, none() )

		result = _get_last_mod_progress([], 'test', item, user, context)
		assert_that( result, none() )

		# Single
		record = MockDBRecord( 1 )
		last_mod = datetime.utcfromtimestamp(1)
		result = _get_last_mod_progress( (record,), 'test', item, user, context)
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_(last_mod))
		assert_that( result.NTIID, is_( 'test' ))

		# Multi
		record2 = MockDBRecord( 10 )
		record3 = MockDBRecord( 0 )
		last_mod = datetime.utcfromtimestamp(10)
		result = _get_last_mod_progress( [record, record2, record3], 'test', item, user, context)
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_(last_mod))
		assert_that( result.LastModified, is_(last_mod))
		assert_that( result.NTIID, is_('test'))

	@time_monotonically_increases
	def test_video_progress(self):
		user = MockUser(u'test_user')
		ntiid = u'ntiid_video'
		item = MockCompletableItem(ntiid)
		context = MockCompletionContext()
		# Non cases
		result = get_progress_for_video_views(ntiid, item, user, context)
		assert_that( result, none() )

		# Single
		timestamp = int(time.time())
		create_video_event(user, ntiid, root_context=context, timestamp=timestamp)
		result = get_progress_for_video_views(ntiid, item, user, context)
		assert_that( result.NTIID, is_( ntiid ))
		assert_that( result.AbsoluteProgress, is_( 31 ))
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.LastModified,
					 is_(datetime.utcfromtimestamp(timestamp)))
		assert_that( result.MaxPossibleProgress, none())
		assert_that( result.MostRecentEndTime, 60)

		# Multiple
		create_video_event(user, ntiid, root_context=context, start=0, max_time_length=30, end=7, time_length=5)
		create_video_event(user, ntiid, root_context=context, start=0, max_time_length=None, end=27, time_length=0)
		timestamp = int(time.time())
		create_video_event(user, ntiid, root_context=context,
						   start=0, max_time_length=30, end=17,
						   time_length=25, timestamp=timestamp)
		result = get_progress_for_video_views(ntiid, item, user, context)
		assert_that( result.NTIID, is_( ntiid ))
		assert_that( result.AbsoluteProgress, is_( 30 )) # we clamp to max_time_length
		assert_that( result.HasProgress, is_( True ))
		assert_that(result.LastModified,
					is_(datetime.utcfromtimestamp(timestamp)))
		assert_that( result.MaxPossibleProgress, is_( 30 ))
		assert_that( result.MostRecentEndTime, is_( 17 ))
