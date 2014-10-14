#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge
import time

from datetime import datetime

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import resource_tags as db_tags
from nti.analytics.database import resource_views as db_views

from nti.analytics.database.resources import Resources

from nti.analytics.database.resource_views import CourseResourceViews
from nti.analytics.database.resource_views import VideoEvents
from nti.analytics.database.resource_views import _get_context_path
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NotesViewed
from nti.analytics.database.resource_tags import HighlightsCreated

from . import DEFAULT_INTID

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
		db_views.create_course_resource_view( test_user_ds_id,
											test_session_id, datetime.now(),
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
		assert_that( resource_view.RootContextID, is_( self.course_id ))
		assert_that( resource_view.resource_id, is_( resource_val ))

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
		results = db_views.get_user_video_events( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 0 ) )
		results = self.session.query( VideoEvents ).all()
		assert_that( results, has_length( 0 ) )

		resource_val = 'ntiid:course_video'
		time_length = 30
		video_event_type = 'WATCH'
		video_start_time = 30
		video_end_time = 60
		with_transcript = True
		db_views.create_video_event( test_user_ds_id,
									test_session_id, datetime.now(),
									self.course_id, self.context_path,
									resource_val, time_length,
									video_event_type, video_start_time,
									video_end_time,  with_transcript )
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

		results = db_views.get_user_video_events( test_user_ds_id, self.course_id )
		results = [x for x in results]
		assert_that( results, has_length( 1 ) )

		resource_view = results[0]
		assert_that( resource_view.user, is_( test_user_ds_id ) )
		assert_that( resource_view.RootContextID, is_( self.course_id ))
		assert_that( resource_view.resource_id, is_( resource_val ))
		assert_that( resource_view.video_start_time, is_( video_start_time ))
		assert_that( resource_view.video_end_time, is_( video_end_time ))
		assert_that( resource_view.with_transcript, is_( with_transcript ))
		assert_that( resource_view.Duration, is_( time_length ))

	@fudge.patch( 'nti.analytics.database.resource_tags._get_sharing_enum' )
	def test_note(self, mock_sharing_enum):
		mock_sharing_enum.is_callable().returns( 'UNKNOWN' )

		results = self.session.query( NotesCreated ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		note_ds_id = DEFAULT_INTID
		note_id = 1
		my_note = MockNote( resource_id, containerId=resource_id, intid=note_ds_id )

		# Create note
		db_tags.create_note( 	test_user_ds_id,
								test_session_id, self.course_id, my_note )

		results = db_tags.get_notes_created_for_course( self.course_id )
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_id ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( self.resource_id ) )
		# 'UNKNOWN' since we cannot access course and it's scopes.
		assert_that( note.sharing, is_( 'UNKNOWN' ) )
		assert_that( note.deleted, none() )
		assert_that( note.timestamp, not_none() )

		# Note view
		db_tags.create_note_view( 	test_user_ds_id,
									test_session_id, datetime.now(),
									self.course_id, my_note )
		results = self.session.query( NotesViewed ).all()
		assert_that( results, has_length( 1 ) )

		note = self.session.query(NotesViewed).one()
		assert_that( note.user_id, is_( 1 ) )
		assert_that( note.session_id, is_( test_session_id ) )
		assert_that( note.course_id, is_( self.course_id ) )
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.resource_id, is_( self.resource_id ) )
		assert_that( note.timestamp, not_none() )

		# Delete note
		db_tags.delete_note( datetime.now(), note_ds_id )

		results = self.session.query(NotesCreated).all()
		assert_that( results, has_length( 1 ) )

		results = db_tags.get_notes_created_for_course( self.course_id )
		assert_that( results, has_length( 0 ) )

		note = self.session.query(NotesCreated).one()
		assert_that( note.note_id, is_( note_id ) )
		assert_that( note.deleted, not_none() )

	def test_highlight(self):
		results = self.session.query( HighlightsCreated ).all()
		assert_that( results, has_length( 0 ) )

		resource_id = 'ntiid:course_resource'
		highlight_ds_id = DEFAULT_INTID
		highlight_id = 1
		my_highlight = MockHighlight( resource_id, intid=highlight_ds_id, containerId=resource_id )

		# Create highlight
		db_tags.create_highlight( 	test_user_ds_id,
									test_session_id, self.course_id, my_highlight )

		results = db_tags.get_highlights_created_for_course( self.course_id )
		assert_that( results, has_length( 1 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.user_id, is_( 1 ) )
		assert_that( highlight.session_id, is_( test_session_id ) )
		assert_that( highlight.course_id, is_( self.course_id ) )
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.resource_id, is_( self.resource_id ) )
		assert_that( highlight.deleted, none() )
		assert_that( highlight.timestamp, not_none() )

		# Delete highlight
		db_tags.delete_highlight( datetime.now(), highlight_ds_id )

		results = self.session.query(HighlightsCreated).all()
		assert_that( results, has_length( 1 ) )

		results = db_tags.get_highlights_created_for_course( self.course_id )
		assert_that( results, has_length( 0 ) )

		highlight = self.session.query(HighlightsCreated).one()
		assert_that( highlight.highlight_id, is_( highlight_id ) )
		assert_that( highlight.deleted, not_none() )
		assert_that( highlight.highlight_ds_id, none() )

	def test_context_path(self):
		path = ['dashboard']
		result = _get_context_path( path )
		assert_that( result, is_( 'dashboard' ))

		path = None
		result = _get_context_path( path )
		assert_that( result, is_( '' ))

		path = [ 'ntiid:lesson1', 'ntiid:overview' ]
		result = _get_context_path( path )
		assert_that( result, is_( 'ntiid:lesson1/ntiid:overview' ))

		path = [ 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:overview' ]
		result = _get_context_path( path )
		assert_that( result, is_( 'ntiid:lesson1/ntiid:overview' ))

		path = [ 'ntiid:overview', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:lesson1', 'ntiid:reading1' ]
		result = _get_context_path( path )
		assert_that( result, is_( 'ntiid:overview/ntiid:lesson1/ntiid:reading1' ))

