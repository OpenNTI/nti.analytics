#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from unittest import TestCase

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import none
from hamcrest import not_none

from nti.analytics.common import timestamp_type

from nti.analytics.database.root_context import _create_course
from nti.analytics.database.boards import create_topic_view
from nti.analytics.database.boards import create_topic
from nti.analytics.database.users import create_user

from nti.analytics.progress import _get_last_mod_progress
from nti.analytics.progress import get_topic_progress

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

from nti.analytics.tests import AnalyticsTestBase

from nti.testing.time import time_monotonically_increases

class MockDBRecord( object ):
	"""
	Mock a database record with a few fields.
	"""

	def  __init__(self, timestamp, time_length=None, MaxDuration=None ):
		self.timestamp = timestamp
		self.time_length = time_length
		self.MaxDuration = MaxDuration

class TestProgress( TestCase ):

	def test_last_mod_progress(self):
		# Non cases
		result = _get_last_mod_progress(None, 'test')
		assert_that( result, none() )

		result = _get_last_mod_progress([], 'test')
		assert_that( result, none() )

		# Single
		record = MockDBRecord( 1 )
		result = _get_last_mod_progress( (record,), 'test')
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_( 1 ))
		assert_that( result.ResourceID, is_( 'test' ))

		# Multi
		record2 = MockDBRecord( 10 )
		record3 = MockDBRecord( 0 )
		result = _get_last_mod_progress( [record, record2, record3], 'test')
		assert_that( result.HasProgress, is_( True ))
		assert_that( result.last_modified, is_( 10 ))
		assert_that( result.LastModified, is_( 10 ))
		assert_that( result.ResourceID, is_( 'test' ))

class TestTopicProgress( AnalyticsTestBase ):

	def setUp(self):
		super( TestTopicProgress, self ).setUp()
		self._install_course()
		self._install_user()
		self._install_topic()

	def _install_user(self):
		self.user = 1
		self.user_id = create_user( self.user ).user_id
		return self.user

	def _install_course(self):
		course_id = 1
		self.course = new_course = CourseInstance()
		setattr( new_course, '_ds_intid', course_id )
		_create_course( self.db, new_course, course_id )
		return new_course

	def _install_topic(self):
		self.topic = CommunityHeadlineTopic()
		self.topic.NTIID = 'tag:ntiid1'
		create_topic( self.user, None, self.course, self.topic)

	def _install_event(self, timestamp, time_length=None):
		create_topic_view(self.user, None, timestamp, self.course, None, self.topic, time_length)

	@time_monotonically_increases
	def test_topic_progress(self):
		# Nothing
		result = get_topic_progress( self.user, self.topic )
		assert_that( result, none() )

		# One
		t1 = timestamp_type( time.time() )
		self._install_event( t1 )
		result = get_topic_progress( self.user, self.topic )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ) )
		assert_that( result.ResourceID, is_( self.topic.NTIID ) )
		assert_that( result.last_modified, is_( t1 ) )

		# Some
		t2 = timestamp_type( time.time() )
		self._install_event( t2 )
		t3 = timestamp_type( time.time() )
		self._install_event( t3, time_length=30 )

		result = get_topic_progress( self.user, self.topic )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ) )
		assert_that( result.ResourceID, is_( self.topic.NTIID ) )
		assert_that( result.last_modified, is_( t3 ) )
