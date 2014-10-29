#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge
import unittest

from datetime import timedelta

from zope import component

from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import not_none

from nti.contenttypes.courses.courses import CourseInstance

from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.database import AnalyticsDB

from nti.analytics.database.courses import Courses
from nti.analytics.database.courses import _create_course

class MockCatalog(object):

	def __init__( self, duration ):
		self.Duration = duration

class TestCourses(unittest.TestCase):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://', testmode=True )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db )
		self.session.close()

	@fudge.patch('nti.analytics.database.courses._course_catalog')
	def test_courses(self, mock_course_catalog):
		mock_catalog = MockCatalog( timedelta( weeks=16 ))
		mock_course_catalog.is_callable().returns( mock_catalog )

		results = self.session.query(Courses).all()
		assert_that( results, has_length( 0 ) )

		my_course = CourseInstance()
		setattr( my_course, 'Duration', timedelta( weeks=16 ) )

		_create_course( self.db, my_course, 1856 )

		results = self.session.query(Courses).all()
		assert_that( results, has_length( 1 ) )
		assert_that( results[0].duration, not_none() )





