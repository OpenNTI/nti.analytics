#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import contains
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import resource_views as db_views

from nti.analytics.database.resources import Resources

from nti.analytics.database.resource_views import CourseResourceViews
from nti.analytics.database.resource_views import VideoEvents
from nti.analytics.database.resource_views import VideoPlaySpeedEvents
from nti.analytics.database._utils import get_context_path

class TestCourseResources(AnalyticsTestBase):

	def setUp(self):
		super( TestCourseResources, self ).setUp()
		self.resource_id = 1
		self.context_path_flat = 'dashboard'
		self.context_path= [ 'dashboard' ]

	def test_resource_view(self):
		results = db_views.get_user_resource_views( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )
		results = self.session.query( CourseResourceViews ).all()
		assert_that( results, has_length( 0 ) )

		resource_val = 'ntiid:course_resource'
		time_length = 30
		event_time = datetime.now()
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, event_time,
											self.course_id, self.context_path,
											resource_val, time_length )
		results = self.session.query(CourseResourceViews).all()
		assert_that( results, has_length( 1 ) )

		resource_view = self.session.query(CourseResourceViews).one()
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( self.context_path_flat ) )
		assert_that( resource_view.resource_id, is_( self.resource_id ) )
		assert_that( resource_view.time_length, is_( time_length ) )

		results = db_views.get_user_resource_views( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		resource_view = results[0]
		assert_that( resource_view.user, is_( test_user_ds_id ) )
		assert_that( resource_view.RootContext, is_( self.course_id ))
		assert_that( resource_view.ResourceId, is_( resource_val ))

		# Idempotent check; our time_length can be updated
		new_time_length = time_length + 1
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, event_time,
											self.course_id, self.context_path,
											resource_val, new_time_length )

		results = self.session.query(CourseResourceViews).all()
		assert_that( results, has_length( 1 ) )

		resource_view = results[0]
		assert_that( resource_view.context_path, is_( self.context_path_flat ) )
		assert_that( resource_view.resource_id, is_( self.resource_id ) )
		assert_that( resource_view.time_length, is_( new_time_length ) )

	def test_resources(self):
		results = self.session.query( Resources ).all()
		assert_that( results, has_length( 0 ) )
		t0 = time.time()
		t1 = time.time() + 1

		resource_val = 'ntiid:course_resource'
		time_length = 30
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, t0,
											self.course_id, self.context_path,
											resource_val, time_length )
		results = self.session.query( Resources ).all()
		assert_that( results, has_length( 1 ) )

		resource_record = results[0]
		assert_that( resource_record.resource_id, is_( self.resource_id ) )
		assert_that( resource_record.resource_ds_id, is_( resource_val ) )

		# Now another insert does not change our Resources table
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, t1,
											self.course_id, self.context_path,
											resource_val, time_length )
		results = self.session.query( Resources ).all()
		assert_that( results, has_length( 1 ) )

		# Now we add a new resource id
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, t0,
											self.course_id, self.context_path,
											'ntiid:course_resource2', time_length )
		results = self.session.query( Resources ).all()
		assert_that( results, has_length( 2 ) )

	def test_video_view(self):
		results = db_views.get_user_video_views( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )
		results = self.session.query( VideoEvents ).all()
		assert_that( results, has_length( 0 ) )

		resource_val = 'ntiid:course_video'
		time_length = 40
		# Note watch time is greater than max
		max_time_length = 30
		video_event_type = 'WATCH'
		video_start_time = 30
		video_end_time = 60
		with_transcript = True
		play_speed = 2
		event_time = datetime.now()
		db_views.create_video_event( test_user_ds_id,
									test_session_id, event_time,
									self.course_id, self.context_path,
									resource_val, time_length, max_time_length,
									video_event_type, video_start_time,
									video_end_time,  with_transcript, play_speed )
		results = self.session.query(VideoEvents).all()
		assert_that( results, has_length( 1 ) )

		resource_view = self.session.query(VideoEvents).one()
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( self.context_path_flat ) )
		assert_that( resource_view.resource_id, is_( self.resource_id ) )
		assert_that( resource_view.video_event_type, is_( video_event_type ) )
		assert_that( resource_view.video_start_time, is_( video_start_time ) )
		assert_that( resource_view.video_end_time, is_( video_end_time ) )
		assert_that( resource_view.time_length, is_( time_length ) )
		assert_that( resource_view.with_transcript )
		assert_that( resource_view.play_speed, is_( str( play_speed )) )

		results = db_views.get_user_video_views( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		resource_view = results[0]
		assert_that( resource_view.user, is_( test_user_ds_id ) )
		assert_that( resource_view.RootContext, is_( self.course_id ))
		assert_that( resource_view.ResourceId, is_( resource_val ))
		assert_that( resource_view.VideoStartTime, is_( video_start_time ))
		assert_that( resource_view.VideoEndTime, is_( video_end_time ))
		assert_that( resource_view.WithTranscript, is_( with_transcript ))
		assert_that( resource_view.Duration, is_( time_length ))

		# Idempotent check; fields can be updated.
		new_time_length = time_length + 1
		new_video_end_time = video_end_time + 1
		db_views.create_video_event( test_user_ds_id,
									test_session_id, event_time,
									self.course_id, self.context_path,
									resource_val, new_time_length, max_time_length,
									video_event_type, video_start_time,
									new_video_end_time,  with_transcript, None )

		results = self.session.query(VideoEvents).all()
		assert_that( results, has_length( 1 ) )

		resource_view = results[0]
		assert_that( resource_view.video_start_time, is_( video_start_time ) )
		assert_that( resource_view.video_end_time, is_( new_video_end_time ) )
		assert_that( resource_view.time_length, is_( new_time_length ) )

	def test_video_start_view(self):
		"""
		Validate video start events (with missing data) can be entered.
		"""
		results = db_views.get_user_video_views( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )
		results = self.session.query( VideoEvents ).all()
		assert_that( results, has_length( 0 ) )

		resource_val = 'ntiid:course_video'
		time_length = max_time_length =  video_end_time = None
		video_start_time = 3
		video_event_type = 'WATCH'
		with_transcript = True
		event_time = datetime.now()
		db_views.create_video_event( test_user_ds_id,
									test_session_id, event_time,
									self.course_id, self.context_path,
									resource_val, time_length, max_time_length,
									video_event_type, video_start_time,
									video_end_time,  with_transcript, None )

		results = self.session.query(VideoEvents).all()
		assert_that( results, has_length( 1 ) )

		resource_view = results[0]
		assert_that( resource_view.video_start_time, is_( video_start_time ) )
		assert_that( resource_view.video_end_time, none() )
		assert_that( resource_view.time_length, none() )

	def test_video_play_speed(self):
		"""
		Validate video play speed events can be entered.
		"""
		results = self.session.query( VideoPlaySpeedEvents ).all()
		assert_that( results, has_length( 0 ) )

		resource_val = 'ntiid:course_video'
		time_length = max_time_length =  video_end_time = None
		video_time = 3
		video_event_type = 'WATCH'
		with_transcript = True
		event_time = video_start_time = datetime.now()
		old_play_speed = 1
		new_play_speed = 2
		db_views.create_play_speed_event( test_user_ds_id,
										test_session_id,
										event_time,
										self.course_id,
										resource_val,
										video_time,
										old_play_speed,
										new_play_speed )

		results = self.session.query(VideoPlaySpeedEvents).all()
		assert_that( results, has_length( 1 ) )

		play_speed = results[0]
		assert_that( play_speed.user_id, is_( 1 ) )
		assert_that( play_speed.session_id, is_( test_session_id ) )
		assert_that( play_speed.timestamp, not_none() )
		assert_that( play_speed.course_id, is_( self.course_id ) )
		assert_that( play_speed.video_play_speed_id, is_( 1 ) )
		assert_that( play_speed.resource_id, is_( self.resource_id ) )
		assert_that( play_speed.video_time, is_( video_time ) )
		assert_that( play_speed.video_view_id, none() )
		assert_that( play_speed.old_play_speed, is_( str( old_play_speed ) ) )
		assert_that( play_speed.new_play_speed, is_( str( new_play_speed ) ) )

		# Now our video watch event, with same timestamp
		# updates our play_speed record with our view id.
		db_views.create_video_event( test_user_ds_id,
									test_session_id, event_time,
									self.course_id, self.context_path,
									resource_val, time_length, max_time_length,
									video_event_type, video_start_time,
									video_end_time,  with_transcript, None )

		results = self.session.query(VideoEvents).all()
		assert_that( results, has_length( 1 ) )

		play_speed = results[0]
		assert_that( play_speed.video_view_id, is_( 1 ) )

		# Now another play speed event, contains the correct view id.
		db_views.create_play_speed_event( test_user_ds_id,
										test_session_id,
										event_time,
										self.course_id,
										resource_val,
										video_time + 1,
										'2x',
										'4x' )

		results = self.session.query(VideoPlaySpeedEvents).all()
		assert_that( results, has_length( 2 ) )

		results = [x.video_view_id for x in results]
		assert_that( results, contains( 1, 1 ) )


	def test_context_path(self):
		path = ['dashboard']
		result = get_context_path( path )
		assert_that( result, is_( 'dashboard' ))

		path = None
		result = get_context_path( path )
		assert_that( result, is_( '' ))

		path = [ 'ntiid:lesson1', 'ntiid:overview' ]
		result = get_context_path( path )
		assert_that( result, is_( 'ntiid:lesson1/ntiid:overview' ))

		path = [ 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:overview' ]
		result = get_context_path( path )
		assert_that( result, is_( 'ntiid:lesson1/ntiid:overview' ))

		path = [ 'ntiid:overview', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:reading1' ]
		result = get_context_path( path )
		assert_that( result, is_( 'ntiid:overview/ntiid:lesson1/ntiid:reading1' ))

