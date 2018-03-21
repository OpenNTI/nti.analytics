#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from datetime import datetime

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import none

from unittest import TestCase

from nti.analytics.progress import _get_last_mod_progress
from nti.analytics.progress import get_progress_for_video_views

from nti.contenttypes.completion.tests.test_models import MockUser
from nti.contenttypes.completion.tests.test_models import MockCompletableItem


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
		user = MockUser(u'test_user')
		item = MockCompletableItem(u'ntiid')
		# Non cases
		result = _get_last_mod_progress(None, 'test', item, user)
		assert_that( result, none() )

		result = _get_last_mod_progress([], 'test', item, user)
		assert_that( result, none() )

		# Single
		record = MockDBRecord( 1 )
		last_mod = datetime.utcfromtimestamp(1)
		result = _get_last_mod_progress( (record,), 'test', item, user)
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_(last_mod))
		assert_that( result.NTIID, is_( 'test' ))

		# Multi
		record2 = MockDBRecord( 10 )
		record3 = MockDBRecord( 0 )
		last_mod = datetime.utcfromtimestamp(10)
		result = _get_last_mod_progress( [record, record2, record3], 'test', item, user)
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_(last_mod))
		assert_that( result.LastModified, is_(last_mod))
		assert_that( result.NTIID, is_('test'))

	def test_video_progress(self):
		user = MockUser(u'test_user')
		ntiid = u'ntiid_video'
		item = MockCompletableItem(ntiid)
		# Non cases
		result = get_progress_for_video_views(ntiid, [], item, user)
		assert_that( result, none() )
		result = get_progress_for_video_views(ntiid, None, item, user)
		assert_that( result, none() )

		# Single
		record = MockDBRecord( timestamp=1 )
		last_mod = datetime.utcfromtimestamp(1)
		records = (record,)
		result = get_progress_for_video_views(ntiid, records, item, user)
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
		result = get_progress_for_video_views(ntiid, records, item, user)
		assert_that( result.NTIID, is_( ntiid ))
		assert_that( result.AbsoluteProgress, is_( 30 ))
		assert_that( result.HasProgress, is_( True ))
		assert_that(result.LastModified,
					is_(datetime.utcfromtimestamp(4)))
		assert_that( result.MaxPossibleProgress, is_( 30 ))
		assert_that( result.MostRecentEndTime, is_( 17 ))
