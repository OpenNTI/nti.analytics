#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import has_length

import time
from datetime import datetime

from nti.externalization import internalization
from nti.externalization.externalization import toExternalObject
from nti.externalization.tests import assert_does_not_pickle

from nti.analytics.model import CourseCatalogViewEvent
from nti.analytics.model import ResourceEvent
from nti.analytics.model import WatchVideoEvent
from nti.analytics.model import SkipVideoEvent
from nti.analytics.model import BatchResourceEvents

from nti.testing.matchers import verifiably_provides

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.interfaces import ICourseCatalogViewEvent
from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IBatchResourceEvents

timestamp = time.mktime( datetime.utcnow().timetuple() )
user = 'jzuech@nextthought.com'
course = 'CS1300'
context_path = 'ntiid:lesson1'
resource_id = 'ntiid:lesson1_chapter1'
time_length = 30

course_catalog_event = CourseCatalogViewEvent(user=user,
					timestamp=timestamp,
					course=course,
					time_length=time_length)

resource_event = ResourceEvent(user=user,
					timestamp=timestamp,
					course=course,
					context_path=context_path,
					resource_id=resource_id,
					time_length=time_length)

video_start_time = 13
video_end_time = 39
with_transcript = True
skip_video_event = SkipVideoEvent(user=user,
					timestamp=timestamp,
					course=course,
					context_path=context_path,
					resource_id=resource_id,
					time_length=time_length,
					video_start_time=video_start_time,
					video_end_time=video_end_time,
					with_transcript=with_transcript)

watch_video_event = WatchVideoEvent(user=user,
				timestamp=timestamp,
				course=course,
				context_path=context_path,
				resource_id=resource_id,
				time_length=time_length,
				video_start_time=video_start_time,
				video_end_time=video_end_time,
				with_transcript=with_transcript)

class TestResourceEvents(NTIAnalyticsTestCase):

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
		assert_that(new_io, has_property('course', is_( course )))
		assert_that(new_io, has_property('time_length', is_( time_length )))
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
		assert_that(new_io, has_property('course', is_( course )))
		assert_that(new_io, has_property('context_path', is_( context_path )))
		assert_that(new_io, has_property('resource_id', is_( resource_id )))
		assert_that(new_io, has_property('time_length', is_( time_length )))
		assert_that( new_io, is_( ResourceEvent ) )

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
		assert_that(new_io, has_property('course', is_( course )))
		assert_that(new_io, has_property('context_path', is_( context_path )))
		assert_that(new_io, has_property('resource_id', is_( resource_id )))
		assert_that(new_io, has_property('time_length', is_( time_length )))
		assert_that(new_io, has_property('event_type', is_( SkipVideoEvent.event_type )))
		assert_that(new_io, has_property('video_start_time', is_( video_start_time )))
		assert_that(new_io, has_property('video_end_time', is_( video_end_time )))
		assert_that(new_io, has_property('with_transcript', is_( with_transcript )))
		assert_that( new_io, is_( SkipVideoEvent ) )

	def test_batch(self):

		batch_events = [ watch_video_event, skip_video_event, resource_event, course_catalog_event ]
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

