#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import time
import pickle
from datetime import datetime

from nti.externalization import internalization
from nti.externalization.externalization import toExternalObject

from nti.analytics.model import ResourceEvent
from nti.analytics.model import BlogViewEvent
from nti.analytics.model import NoteViewEvent
from nti.analytics.model import SkipVideoEvent
from nti.analytics.model import TopicViewEvent
from nti.analytics.model import WatchVideoEvent
from nti.analytics.model import AnalyticsSession
from nti.analytics.model import AnalyticsSessions
from nti.analytics.model import BatchResourceEvents
from nti.analytics.model import CourseCatalogViewEvent
from nti.analytics.model import VideoPlaySpeedChangeEvent
from nti.analytics.model import AnalyticsClientParams
from nti.analytics.model import SelfAssessmentViewEvent
from nti.analytics.model import AssignmentViewEvent
from nti.analytics.model import ProfileViewEvent
from nti.analytics.model import ProfileActivityViewEvent
from nti.analytics.model import ProfileMembershipViewEvent

from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import IBlogViewEvent
from nti.analytics.interfaces import INoteViewEvent
from nti.analytics.interfaces import ITopicViewEvent
from nti.analytics.interfaces import IAnalyticsSessions
from nti.analytics.interfaces import IBatchResourceEvents
from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import IProfileViewEvent
from nti.analytics.interfaces import IProfileActivityViewEvent
from nti.analytics.interfaces import IProfileMembershipViewEvent
from nti.analytics.interfaces import IVideoPlaySpeedChangeEvent
from nti.analytics.interfaces import ISelfAssessmentViewEvent
from nti.analytics.interfaces import IAssignmentViewEvent
from nti.analytics.interfaces import IProgress
from nti.analytics.interfaces import IAnalyticsClientParams
from nti.analytics.interfaces import DEFAULT_ANALYTICS_BATCH_SIZE
from nti.analytics.interfaces import DEFAULT_ANALYTICS_FREQUENCY

from nti.analytics.progress import DefaultProgress

from nti.externalization.tests import assert_does_not_pickle

from nti.testing.matchers import verifiably_provides

from nti.analytics.tests import NTIAnalyticsTestCase

timestamp = time.mktime( datetime.utcnow().timetuple() )
user = 'jzuech@nextthought.com'
entity = 'ou.nextthought.com'
course = 'CS1300'
context_path = ['ntiid:lesson1']
resource_id = 'ntiid:lesson1_chapter1'
time_length = 30
max_time_length = 30

topic_id = 'ntiid:topic1'
blog_id = 'ntiid:blog1'
note_id = 'ntiid:note1'

blog_event = BlogViewEvent(user=user,
					timestamp=timestamp,
					blog_id=blog_id,
					Duration=time_length)

note_event = NoteViewEvent(user=user,
					timestamp=timestamp,
					RootContextID=course,
					note_id=note_id,
					Duration=time_length)

topic_event = TopicViewEvent(user=user,
					timestamp=timestamp,
					RootContextID=course,
					topic_id=topic_id,
					Duration=time_length)

course_catalog_event = CourseCatalogViewEvent(user=user,
					timestamp=timestamp,
					RootContextID=course,
					Duration=time_length)

resource_kwargs = { 'user':user,
					'timestamp':timestamp,
					'RootContextID':course,
					'context_path':context_path,
					'ResourceId':resource_id,
					'Duration':time_length }

resource_event = ResourceEvent( **resource_kwargs )

self_assess_kwargs = dict( **resource_kwargs )
self_assess_kwargs['ContentId'] = self_assess_kwargs.pop( 'ResourceId' )
self_assess_kwargs['ResourceId'] = question_set_id = 'tag:nextthought,2011-05-01-selfasssessss1'
self_assessment_event = SelfAssessmentViewEvent( **self_assess_kwargs )

assignment_kwargs = dict( **resource_kwargs )
assignment_kwargs['ResourceId'] = assignment_id = 'tag:nextthought,2011-05-01-assign1'
assignment_event = AssignmentViewEvent( **assignment_kwargs )

video_start_time = 13
video_end_time = 39
with_transcript = True
skip_video_event = SkipVideoEvent(user=user,
					timestamp=timestamp,
					RootContextID=course,
					context_path=context_path,
					ResourceId=resource_id,
					Duration=time_length,
					video_start_time=video_start_time,
					video_end_time=video_end_time,
					with_transcript=with_transcript)

watch_video_event = WatchVideoEvent(user=user,
				timestamp=timestamp,
				RootContextID=course,
				context_path=context_path,
				ResourceId=resource_id,
				Duration=time_length,
				MaxDuration=max_time_length,
				video_start_time=video_start_time,
				video_end_time=video_end_time,
				with_transcript=with_transcript)

start_video_event = WatchVideoEvent(user=user,
				timestamp=timestamp,
				RootContextID=course,
				context_path=context_path,
				ResourceId=resource_id,
				Duration=None,
				MaxDuration=max_time_length,
				video_start_time=video_start_time,
				video_end_time=None,
				with_transcript=with_transcript)

old_play_speed = 2
new_play_speed = 4
play_speed_event = VideoPlaySpeedChangeEvent(
				user=user,
				timestamp=timestamp,
				RootContextID=course,
				ResourceId=resource_id,
				OldPlaySpeed=old_play_speed,
				NewPlaySpeed=new_play_speed,
				VideoTime=video_start_time )

profile_event = ProfileViewEvent(user=user,
					timestamp=timestamp,
					ProfileEntity=entity,
					Duration=time_length)

profile_activity_event = ProfileActivityViewEvent(user=user,
					timestamp=timestamp,
					ProfileEntity=entity,
					Duration=time_length)

profile_membership_event = ProfileMembershipViewEvent(user=user,
					timestamp=timestamp,
					ProfileEntity=entity,
					Duration=time_length)

session = AnalyticsSession( SessionStartTime=timestamp, SessionEndTime=timestamp+1 )

class TestResourceEvents(NTIAnalyticsTestCase):

	def test_blog_event(self):

		assert_that(blog_event, verifiably_provides( IBlogViewEvent ) )

		ext_obj = toExternalObject(blog_event)
		assert_that(ext_obj, has_entry('Class', 'BlogViewEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.blogviewevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property('blog_id', is_( blog_id )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, is_( BlogViewEvent ) )

	def test_note_event(self):

		assert_that(note_event, verifiably_provides( INoteViewEvent ) )

		ext_obj = toExternalObject(note_event)
		assert_that(ext_obj, has_entry('Class', 'NoteViewEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.noteviewevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property('note_id', is_( note_id )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, is_( NoteViewEvent ) )

	def test_topic_event(self):

		assert_that(topic_event, verifiably_provides( ITopicViewEvent ) )

		ext_obj = toExternalObject(topic_event)
		assert_that(ext_obj, has_entry('Class', 'TopicViewEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.topicviewevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property('topic_id', is_( topic_id )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, is_( TopicViewEvent ) )

	def test_course_catalog_event(self):

		assert_that(course_catalog_event, verifiably_provides( ICourseCatalogViewEvent ) )

		ext_obj = toExternalObject(course_catalog_event)
		assert_that(ext_obj, has_entry('Class', 'CourseCatalogViewEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.coursecatalogviewevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, is_( CourseCatalogViewEvent ) )

	def test_resource_event(self):

		assert_that(resource_event, verifiably_provides( IResourceEvent ) )

		ext_obj = toExternalObject(resource_event)
		assert_that(ext_obj, has_entry('Class', 'ResourceEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.resourceevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property('context_path', is_( context_path )))
		assert_that(new_io, has_property('ResourceId', is_( resource_id )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, is_( ResourceEvent ) )

	def test_self_assess_event(self):
		assert_that(self_assessment_event, verifiably_provides( ISelfAssessmentViewEvent ) )

		ext_obj = toExternalObject(self_assessment_event)
		assert_that(ext_obj, has_entry('Class', 'SelfAssessmentViewEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.selfassessmentviewevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property( 'user', is_( user )))
		assert_that(new_io, has_property( 'timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property( 'context_path', is_( context_path )))
		assert_that(new_io, has_property( 'ContentId', is_( resource_id )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, has_property( 'QuestionSetId', is_( question_set_id )))
		assert_that( new_io, is_( SelfAssessmentViewEvent ) )

	def _do_test_assigment_json(self, new_io, ext_obj):
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property( 'user', is_( user )))
		assert_that(new_io, has_property( 'timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property( 'context_path', is_( context_path )))
		assert_that(new_io, has_property( 'ContentId', none()))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that( new_io, has_property( 'AssignmentId', is_( assignment_id )))
		assert_that( new_io, has_property( 'ResourceId', is_( assignment_id )))
		assert_that( new_io, is_( AssignmentViewEvent ) )

	def test_assignment_event(self):
		assert_that(assignment_event, verifiably_provides( IAssignmentViewEvent ) )

		ext_obj = toExternalObject(assignment_event)
		assert_that(ext_obj, has_entry('Class', 'AssignmentViewEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.assignmentviewevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		self._do_test_assigment_json( new_io, ext_obj )

		# Validate we can accept legacy field names.
		resource_id = ext_obj.pop( 'ResourceId' )
		ext_obj[ 'resource_id' ] = resource_id
		new_io = factory()
		self._do_test_assigment_json( new_io, ext_obj )

	def test_video_event(self):
		assert_that(skip_video_event, verifiably_provides( IVideoEvent ) )

		ext_obj = toExternalObject(skip_video_event)
		assert_that(ext_obj, has_entry('Class', 'SkipVideoEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.skipvideoevent' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property('context_path', is_( context_path )))
		assert_that(new_io, has_property('ResourceId', is_( resource_id )))
		assert_that(new_io, has_property( 'Duration', is_( time_length )))
		assert_that(new_io, has_property('event_type', is_( SkipVideoEvent.event_type )))
		assert_that(new_io, has_property('video_start_time', is_( video_start_time )))
		assert_that(new_io, has_property('video_end_time', is_( video_end_time )))
		assert_that(new_io, has_property('with_transcript', is_( with_transcript )))
		assert_that( new_io, is_( SkipVideoEvent ) )

		# With max duration
		skip_video_event.MaxDuration = 60
		ext_obj = toExternalObject(skip_video_event)
		factory = internalization.find_factory_for(ext_obj)
		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('MaxDuration', is_( 60 )))

	def test_video_play_speed_event(self):
		assert_that(play_speed_event, verifiably_provides( IVideoPlaySpeedChangeEvent ) )

		ext_obj = toExternalObject(play_speed_event)
		assert_that(ext_obj, has_entry('Class', 'VideoPlaySpeedChangeEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.videoplayspeedchange' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property('RootContextID', is_( course )))
		assert_that(new_io, has_property('ResourceId', is_( resource_id )))
		assert_that(new_io, has_property('OldPlaySpeed', is_( old_play_speed )))
		assert_that(new_io, has_property('NewPlaySpeed', is_( new_play_speed )))
		assert_that(new_io, has_property('VideoTime', is_( video_start_time )))
		assert_that( new_io, is_( VideoPlaySpeedChangeEvent ) )

	def test_video_start_event(self):
		assert_that(start_video_event, verifiably_provides( IVideoEvent ) )
		ext_obj = toExternalObject(start_video_event)

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property( 'RootContextID', is_( course )))
		assert_that(new_io, has_property('context_path', is_( context_path )))
		assert_that(new_io, has_property('ResourceId', is_( resource_id )))
		assert_that(new_io, has_property( 'Duration', none()))
		assert_that(new_io, has_property('event_type', is_( WatchVideoEvent.event_type )))
		assert_that(new_io, has_property('video_start_time', is_( video_start_time )))
		assert_that(new_io, has_property('video_end_time', none()))
		assert_that(new_io, has_property('with_transcript', is_( with_transcript )))

	def test_video_event_andrew(self):

		ext_obj = {
			"course":"tag:nextthought.com,2011-10:system-OID-0x7e30:5573657273:YV7ubjAxx3S",
			"with_transcript":"false",
			"video_start_time":0,
			"video_end_time":30,
			"context_path": ["a test"],
			"resource_id":"1500101:0_ey2kllmp",
			"time_length":24791,
			"MimeType":"application/vnd.nextthought.analytics.watchvideoevent",
			"user":"andrew.ligon",
			"timestamp": 1407645254.609799}

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()

		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('with_transcript', is_( False )))
		assert_that(new_io, has_property('user', is_( 'andrew.ligon' )))
		assert_that(new_io, has_property('RootContextID', is_( "tag:nextthought.com,2011-10:system-OID-0x7e30:5573657273:YV7ubjAxx3S" )))
		assert_that(new_io, has_property('context_path', is_( ['a test'] )))
		assert_that(new_io, has_property('ResourceId', is_( '1500101:0_ey2kllmp' )))
		assert_that(new_io, has_property('Duration', is_( 24791 )))
		assert_that(new_io, has_property('time_length', is_( 24791 )))
		assert_that(new_io, has_property('event_type', is_( WatchVideoEvent.event_type )))
		assert_that(new_io, has_property('video_start_time', is_( 0 )))
		assert_that(new_io, has_property('video_end_time', is_( 30 )))
		assert_that(new_io, has_property('timestamp', is_( 1407645254.609799 )))

		assert_that( new_io, is_( WatchVideoEvent ) )

	def test_batch(self):
		batch_events = [ 	watch_video_event, skip_video_event, resource_event,
							course_catalog_event, blog_event, note_event, topic_event,
							play_speed_event, self_assessment_event, assignment_event ]
		batch_count = len( batch_events )
		io = BatchResourceEvents( events=batch_events )
		assert_does_not_pickle(io)
		assert_that(io, verifiably_provides( IBatchResourceEvents ) )

		ext_obj = toExternalObject(io)
		assert_that(ext_obj, has_entry('Class', 'BatchResourceEvents'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.batchevents' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that( new_io.events, has_length( batch_count ) )
		assert_that( new_io, is_( BatchResourceEvents ) )

		# Test iterable
		assert_that( new_io, has_length( batch_count ) )
		events = [x for x in new_io]
		assert_that( events, not_none() )
		assert_that( events, has_length( batch_count ))

	def test_sessions(self):
		sessions = [ session, session, session ]

		session_count = len( sessions )
		io = AnalyticsSessions( sessions=sessions )
		assert_does_not_pickle(io)
		assert_that( io, verifiably_provides( IAnalyticsSessions ) )

		ext_obj = toExternalObject(io)
		assert_that(ext_obj, has_entry('Class', 'AnalyticsSessions'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.analyticssessions' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that( new_io.sessions, has_length( session_count ) )
		assert_that( new_io, is_( AnalyticsSessions ) )

		# Test iterable
		assert_that( new_io, has_length( session_count ) )
		sessions = [x for x in new_io]
		assert_that( sessions, not_none() )
		assert_that( sessions, has_length( session_count ))
		assert_that( sessions[0], is_( AnalyticsSession ) )

	def test_pickle_legacy(self):
		ve = ResourceEvent()
		del ve.Duration
		del ve.RootContextID
		ve.__dict__['course'] = 'foo'
		ve.__dict__['time_length'] = 10
		f_string = pickle.dumps(ve)
		f_new = pickle.loads(f_string)
		assert_that(f_new, has_property('Duration', 10))
		assert_that(f_new, has_property('RootContextID', 'foo'))

	def _do_test_profile(self, event, event_type):
		assert_that(event, verifiably_provides( event_type ) )
		ext_obj = toExternalObject(event)
		assert_that(ext_obj, has_entry('Class', event.__external_class_name__ ))
		assert_that(ext_obj, has_entry('MimeType', event.mimeType ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that(new_io, has_property('user', is_( user )))
		assert_that(new_io, has_property('timestamp', is_( timestamp )))
		assert_that(new_io, has_property('context_path', none()))
		assert_that(new_io, has_property('Duration', is_( time_length ) ))
		assert_that(new_io, has_property('ProfileEntity', is_( entity )))

	def test_profile(self):
		self._do_test_profile( profile_event, IProfileViewEvent )

	def test_profile_activity(self):
		self._do_test_profile( profile_activity_event, IProfileActivityViewEvent )

	def test_profile_membership(self):
		self._do_test_profile( profile_membership_event, IProfileMembershipViewEvent )

class TestProgress(NTIAnalyticsTestCase):

	def test_progress(self):
		resource_id = 'tag:nt_ntiid1'
		last_modified = datetime.utcnow()
		progress = DefaultProgress( resource_id, 10, 20, True, last_modified )
		assert_that( progress, verifiably_provides( IProgress ) )

		ext_obj = toExternalObject( progress )
		assert_that(ext_obj, has_entry( 'AbsoluteProgress', 10 ))
		assert_that(ext_obj, has_entry( 'MaxPossibleProgress', 20 ))
		assert_that(ext_obj, has_entry( 'HasProgress', True ))
		assert_that(ext_obj, has_entry( 'Last Modified', last_modified ))
		assert_that(ext_obj, has_entry( 'ResourceID', resource_id ))
		assert_that(ext_obj, has_entry( 'Class', 'Progress' ))
		assert_that(ext_obj, has_entry( 'MimeType', 'application/vnd.nextthought.progress' ))

class TestClientParams(NTIAnalyticsTestCase):

	def test_progress(self):

		client_params = AnalyticsClientParams()
		assert_that( client_params, verifiably_provides( IAnalyticsClientParams ) )

		ext_obj = toExternalObject( client_params )
		assert_that(ext_obj, has_entry( 'RecommendedBatchEventsSize', DEFAULT_ANALYTICS_BATCH_SIZE ))
		assert_that(ext_obj, has_entry( 'RecommendedBatchEventsSendFrequency', DEFAULT_ANALYTICS_FREQUENCY ))
		assert_that(ext_obj, has_entry( 'RecommendedBatchSessionsSize', DEFAULT_ANALYTICS_BATCH_SIZE ))
		assert_that(ext_obj, has_entry( 'RecommendedBatchSessionsSendFrequency', DEFAULT_ANALYTICS_FREQUENCY ))
		assert_that(ext_obj, has_entry( 'RecommendedAnalyticsSyncInterval', DEFAULT_ANALYTICS_FREQUENCY ))
