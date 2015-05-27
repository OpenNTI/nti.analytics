#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.tests import test_user_ds_id
from nti.analytics.tests import test_session_id
from nti.analytics.tests import AnalyticsTestBase

from nti.analytics.database import resource_views as db_views

from nti.analytics.resource_views import get_progress_for_ntiid
from nti.analytics.resource_views import get_video_progress_for_course

from nti.testing.time import time_monotonically_increases

class TestResourceViews(AnalyticsTestBase):

	def setUp(self):
		super( TestResourceViews, self ).setUp()
		self.resource_id = 1
		self.context_path_flat = 'dashboard'
		self.context_path= [ 'dashboard' ]

	def _create_video_event(self, user_id, resource_val, course_id=None, max_time_length=None):
		time_length = 30
		video_event_type = 'WATCH'
		video_start_time = 30
		video_end_time = 60
		course_id = course_id or self.course_id
		with_transcript = True
		event_time = time.time()
		db_views.create_video_event( user_id,
									test_session_id, event_time,
									course_id, self.context_path,
									resource_val, time_length, max_time_length,
									video_event_type, video_start_time,
									video_end_time,  with_transcript, None )


	def _create_resource_view(self, user_id, resource_val):
		time_length = 30
		event_time = time.time()
		db_views.create_course_resource_view( user_id,
											test_session_id, event_time,
											self.course_id, self.context_path,
											resource_val, time_length )

	@time_monotonically_increases
	def test_progress(self):
		resource_ntiid = 'tag:resource_id'
		video_ntiid = 'tag:video_id'
		progress = get_progress_for_ntiid( test_user_ds_id, resource_ntiid )
		assert_that( progress, none() )

		# Create resource view
		self._create_resource_view( test_user_ds_id, resource_ntiid )
		progress = get_progress_for_ntiid( test_user_ds_id, resource_ntiid )
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )

		progress = get_progress_for_ntiid( test_user_ds_id, video_ntiid )
		assert_that( progress, none() )

		# Video view
		self._create_video_event( test_user_ds_id, video_ntiid, max_time_length=60 )

		progress = get_progress_for_ntiid( test_user_ds_id, resource_ntiid )
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )

		progress = get_progress_for_ntiid( test_user_ds_id, video_ntiid )
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )
		assert_that( progress.AbsoluteProgress, is_( 30 ) )
		assert_that( progress.MaxPossibleProgress, is_( 60 ) )

		# Dupe does not change anything
		self._create_resource_view( test_user_ds_id, resource_ntiid )
		self._create_video_event( test_user_ds_id, video_ntiid  )

		progress = get_progress_for_ntiid( test_user_ds_id, resource_ntiid )
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )

		progress = get_progress_for_ntiid( test_user_ds_id, video_ntiid )
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )
		assert_that( progress.AbsoluteProgress, is_( 60 ) )
		assert_that( progress.MaxPossibleProgress, is_( 60 ) )

	@time_monotonically_increases
	def test_course_video_progress(self):
		video_ntiid = 'tag:video_id'
		progresses = get_video_progress_for_course( test_user_ds_id, self.course_id )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( 0 ) )

		# Video view
		self._create_video_event( test_user_ds_id, video_ntiid )

		progresses = get_video_progress_for_course( test_user_ds_id, self.course_id )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( 1 ) )

		# Dupe does not change anything
		# Specify max time length.
		self._create_video_event( test_user_ds_id, video_ntiid, max_time_length=60 )

		progresses = get_video_progress_for_course( test_user_ds_id, self.course_id )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( 1 ) )

		# Multiple videos
		video_count = 5
		for x in range( video_count ):
			self._create_video_event( test_user_ds_id, video_ntiid + '_' + str( x ) )

		progresses = get_video_progress_for_course( test_user_ds_id, self.course_id )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( video_count + 1 ) )

		# Different course changes nothing
		for x in range( video_count ):
			self._create_video_event( test_user_ds_id, video_ntiid + '_' + str( x ), course_id=9999 )

		progresses = get_video_progress_for_course( test_user_ds_id, self.course_id )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( video_count + 1 ) )


