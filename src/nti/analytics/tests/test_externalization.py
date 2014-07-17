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

from nti.analytics.model import ResourceEvent
from nti.analytics.model import VideoEvent
from nti.analytics.model import BatchResourceEvents

from nti.testing.matchers import verifiably_provides

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics.interfaces import IResourceEvent
from nti.analytics.interfaces import IVideoEvent
from nti.analytics.interfaces import IBatchResourceEvents

class TestResourceEvents(NTIAnalyticsTestCase):

	def test_resource_event(self):
		timestamp = time.mktime( datetime.utcnow().timetuple() )
		user = 'jzuech@nextthought.com'
		course = 'CS1300'
		context_path = 'ntiid:lesson1'
		resource_id = 'ntiid:lesson1_chapter1'
		time_length = 30
		io = ResourceEvent(user=user,
							timestamp=timestamp,
							course=course,
							context_path=context_path,
							resource_id=resource_id,
							time_length=time_length)
		assert_that(io, verifiably_provides( IResourceEvent ) )
		assert_does_not_pickle(io)

		ext_obj = toExternalObject(io)
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
		timestamp = time.mktime( datetime.utcnow().timetuple() )
		user = 'jzuech@nextthought.com'
		course = 'CS1300'
		context_path = 'ntiid:lesson1'
		resource_id = 'ntiid:lesson1_chapter1'
		time_length = 30
		event_type = 'WATCH'
		video_start_time = 13
		video_end_time = 39
		with_transcript = True
		io = VideoEvent(user=user,
						timestamp=timestamp,
						course=course,
						context_path=context_path,
						resource_id=resource_id,
						time_length=time_length,
						event_type=event_type,
						video_start_time=video_start_time,
						video_end_time=video_end_time,
						with_transcript=with_transcript)
		assert_that(io, verifiably_provides( IVideoEvent ) )
		assert_does_not_pickle(io)

		ext_obj = toExternalObject(io)
		assert_that(ext_obj, has_entry('Class', 'VideoEvent'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.videoevent' ))

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
		assert_that(new_io, has_property('event_type', is_( event_type )))
		assert_that(new_io, has_property('video_start_time', is_( video_start_time )))
		assert_that(new_io, has_property('video_end_time', is_( video_end_time )))
		assert_that(new_io, has_property('with_transcript', is_( with_transcript )))
		assert_that( new_io, is_( VideoEvent ) )

	def test_batch(self):
		timestamp = time.mktime( datetime.utcnow().timetuple() )
		user = 'jzuech@nextthought.com'
		course = 'CS1300'
		context_path = 'ntiid:lesson1'
		resource_id = 'ntiid:lesson1_chapter1'
		time_length = 30
		event_type = 'WATCH'
		video_start_time = 13
		video_end_time = 39
		with_transcript = True

		video_event = VideoEvent(user=user,
						timestamp=timestamp,
						course=course,
						context_path=context_path,
						resource_id=resource_id,
						time_length=time_length,
						event_type=event_type,
						video_start_time=video_start_time,
						video_end_time=video_end_time,
						with_transcript=with_transcript)

		resource_event = ResourceEvent(user=user,
							timestamp=timestamp,
							course=course,
							context_path=context_path,
							resource_id=resource_id,
							time_length=time_length)

		io = BatchResourceEvents( events=[ video_event, resource_event ] )

		ext_obj = toExternalObject(io)
		assert_that(ext_obj, has_entry('Class', 'BatchResourceEvents'))
		assert_that(ext_obj, has_entry('MimeType', 'application/vnd.nextthought.analytics.batchevents' ))

		factory = internalization.find_factory_for(ext_obj)
		assert_that(factory, is_(not_none()))

		new_io = factory()
		internalization.update_from_external_object(new_io, ext_obj)
		assert_that( new_io.events, has_length( 2 ) )
		assert_that( new_io, is_( BatchResourceEvents ) )

		# Test iterable
		events = [x for x in new_io.events]
		assert_that( events, not_none() )
		assert_that( events, has_length( 2 ))
