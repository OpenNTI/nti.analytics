#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database.interfaces import IAnalyticsDB

from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.database.metadata import CourseEnrollments
from nti.analytics.database.metadata import CourseDrops

from nti.contenttypes.courses import courses
from nti.contenttypes.courses import interfaces

from nti.dataserver.users import User

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestEnrollments( NTIAnalyticsTestCase ):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db, provided=IAnalyticsDB )
		self.session.close()

	def _shared_setup(self):
		principal = User.create_user( username='sjohnson@nextthought.com', dataserver=self.ds )
		self.ds.root[principal.id] = principal

		admin = courses.CourseAdministrativeLevel()
		self.ds.root['admin'] = admin
		course = courses.CourseInstance()
		admin['course'] = course

		self.section = course.SubInstances['section1'] = courses.ContentCourseSubInstance()

		self.principal  = principal
		self.course = course

	@WithMockDSTrans
	def test_enrollments(self):
		self._shared_setup()

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 0 ) )

		# Enroll
		manager = interfaces.ICourseEnrollmentManager(self.course)
		record = manager.enroll(self.principal, scope='Public')

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )
		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 0 ) )

		# Drop
		manager = interfaces.ICourseEnrollmentManager(record.CourseInstance)
		manager.drop(self.principal)

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 1 ) )


