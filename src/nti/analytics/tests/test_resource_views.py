#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time
import fudge
import zope.intid

from zope import component

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import contains_inanyorder

from nti.analytics.database import resource_views as db_views

from nti.analytics.progress import get_progress_for_video_views
from nti.analytics.progress import get_progress_for_resource_views
from nti.analytics.progress import get_video_progress_for_course

from nti.analytics.resource_views import get_video_views
from nti.analytics.resource_views import get_video_views_for_ntiid
from nti.analytics.resource_views import get_user_video_views_for_ntiid
from nti.analytics.resource_views import get_user_resource_views_for_ntiid
from nti.analytics.resource_views import get_watched_segments_for_ntiid

from nti.analytics.tests import test_session_id
from nti.analytics.tests import AnalyticsTestBase
from nti.analytics.tests import NTIAnalyticsTestCase

from nti.contenttypes.completion.tests.test_models import MockUser
from nti.contenttypes.completion.tests.test_models import MockCompletableItem
from nti.contenttypes.completion.tests.test_models import MockCompletionContext

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import Community

from nti.testing.time import time_monotonically_increases

test_user_ds_id = MockUser(u'78')


def _create_video_event(user_id, resource_val, root_context=None, max_time_length=None, start=30, end=60, time_length=None, timestamp=None):
	time_length = end-start if time_length is None else time_length
	video_event_type = 'WATCH'
	video_start_time = start
	video_end_time = end
	root_context = root_context or 1
	with_transcript = True
	event_time = timestamp or time.time()
	db_views.create_video_event(user_id,
								test_session_id, event_time,
								root_context, [ u'dashboard' ],
								resource_val, time_length, max_time_length,
								video_event_type, video_start_time,
								video_end_time,  with_transcript, None, None )
create_video_event = _create_video_event


class TestResourceProgress(AnalyticsTestBase):

	def setUp(self):
		super( TestResourceProgress, self ).setUp()
		self.resource_id = 1
		self.context_path_flat = u'dashboard'
		self.context_path= [ u'dashboard' ]

	def _create_resource_view(self, user_id, resource_val):
		time_length = 30
		event_time = time.time()
		db_views.create_course_resource_view(user_id,
											 test_session_id, event_time,
											 self.course_id, self.context_path,
											 resource_val, time_length )

	@time_monotonically_increases
	def test_progress(self):
		resource_ntiid = u'tag:resource_id'
		video_ntiid = u'tag:video_id'
		user = test_user_ds_id
		item = MockCompletableItem(u'ntiid')
		context = MockCompletionContext()
		events = get_user_resource_views_for_ntiid(test_user_ds_id, resource_ntiid)
		progress = get_progress_for_resource_views(resource_ntiid, events, item, user, context)
		assert_that( progress, none() )

		# Create resource view
		self._create_resource_view( test_user_ds_id, resource_ntiid )
		events = get_user_resource_views_for_ntiid(test_user_ds_id, resource_ntiid)
		progress = get_progress_for_resource_views(resource_ntiid, events, item, user, context)
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )

		progress = get_progress_for_video_views(video_ntiid, item, user, context)
		assert_that( progress, none() )

		# Video view
		_create_video_event( test_user_ds_id,
							 video_ntiid,
							 root_context=context,
							 max_time_length=60 )

		progress = get_progress_for_video_views(video_ntiid, item, user, context)
		assert_that( progress, not_none() )
		assert_that( progress.AbsoluteProgress, is_( 31 ) )
		assert_that( progress.MaxPossibleProgress, is_( 60 ) )

		# Dupe does not change anything
		self._create_resource_view( test_user_ds_id, resource_ntiid )
		_create_video_event( test_user_ds_id, video_ntiid  )

		events = get_user_resource_views_for_ntiid(test_user_ds_id, resource_ntiid)
		progress = get_progress_for_resource_views(resource_ntiid, events, item, user, context)
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )

		progress = get_progress_for_video_views(video_ntiid, item, user, context)
		assert_that( progress, not_none() )
		assert_that( progress.HasProgress, is_( True ) )
		assert_that( progress.AbsoluteProgress, is_( 31 ) )
		assert_that( progress.MaxPossibleProgress, is_( 60 ) )

	@time_monotonically_increases
	@fudge.patch('nti.analytics.resource_views.find_object_with_ntiid')
	def test_course_video_progress(self, mock_find_object):
		video_ntiid = u'tag:video_id'
		item = MockCompletableItem(video_ntiid)
		# Events are stored with a course with intid of 1
		context = MockCompletionContext()
		context._ds_intid = 1
		mock_find_object.is_callable().returns(item)
		progresses = get_video_progress_for_course( test_user_ds_id, context )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( 0 ) )

		# Video view
		_create_video_event(test_user_ds_id, video_ntiid, root_context=context)

		progresses = get_video_progress_for_course( test_user_ds_id, context )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( 1 ) )

		# Dupe does not change anything
		# Specify max time length.
		_create_video_event(test_user_ds_id,
						video_ntiid,
						max_time_length=60,
						root_context=context)

		progresses = get_video_progress_for_course(test_user_ds_id, context)
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( 1 ) )

		# Multiple videos
		video_count = 5
		for x in range( video_count ):
			_create_video_event(test_user_ds_id,
								video_ntiid + '_' + str( x ),
								root_context=context)

		progresses = get_video_progress_for_course( test_user_ds_id, context )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( video_count + 1 ) )

		# Different course changes nothing
		for x in range( video_count ):
			_create_video_event(test_user_ds_id, video_ntiid + '_' + str( x ),
								root_context=9999)

		progresses = get_video_progress_for_course( test_user_ds_id, context )
		assert_that( progresses, not_none() )
		assert_that( progresses, has_length( video_count + 1 ) )


class TestResourceViews( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@time_monotonically_increases
	def test_video_view(self):
		# Community based
		video_ntiid = u'tag:video_id'
		intids = component.getUtility( zope.intid.IIntIds )
		course = CourseInstance()
		intids.register( course )
		community = Community.create_community( username=u'community_name' )
		_create_video_event( test_user_ds_id, video_ntiid, community )

		# Empty
		results = get_video_views_for_ntiid( 'tag:nextthought.com,2011-10:dne' )
		assert_that( results, has_length( 0 ))

		results = get_video_views_for_ntiid( video_ntiid )
		assert_that( results, has_length( 1 ))
		views = get_video_views()
		assert_that( views, has_length( 1 ))
		view = views[0]
		assert_that( view.RootContext, is_( community ))

		# Course based
		_create_video_event( test_user_ds_id, video_ntiid, course )
		views = get_video_views( course=course )
		assert_that( views, has_length( 1 ))
		view = views[0]
		assert_that( view.RootContext, is_( course ))

		results = get_video_views_for_ntiid( video_ntiid )
		assert_that( results, has_length( 2 ))

	@WithMockDSTrans
	@time_monotonically_increases
	def test_video_segments(self):

		video_ntiid = u'tag:video_id'
		course = CourseInstance()

		results = get_watched_segments_for_ntiid(video_ntiid)
		assert_that(results, has_length(0))
		
		_create_video_event( test_user_ds_id, video_ntiid, course )
		_create_video_event( test_user_ds_id, video_ntiid, course )

		results = get_watched_segments_for_ntiid(video_ntiid)

		assert_that(results, is_([(30, 60, 2)]))

		_create_video_event( test_user_ds_id, video_ntiid, course, start=100, end=200)

		results = get_watched_segments_for_ntiid(video_ntiid)

		assert_that(results,
					contains_inanyorder((30, 60, 2),
										(100, 200, 1)))

	@WithMockDSTrans
	@time_monotonically_increases
	def test_video_segments_ignores_bad_data(self):

		video_ntiid = u'tag:video_id'
		course = CourseInstance()

		_create_video_event( test_user_ds_id, video_ntiid, course, start=100, end=200)
		_create_video_event( test_user_ds_id, video_ntiid, course, start=10000, end=200)
		results = get_watched_segments_for_ntiid(video_ntiid)

		assert_that(results, is_([(100, 200, 1)]))
