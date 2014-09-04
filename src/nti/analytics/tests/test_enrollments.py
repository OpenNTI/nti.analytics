#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from fudge import patch_object
from zope import component

from hamcrest import assert_that
from hamcrest import has_length

from nti.contenttypes.courses import courses
from nti.contenttypes.courses import interfaces

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics import identifier

from nti.analytics.database.database import AnalyticsDB
from nti.analytics.database.interfaces import IAnalyticsDB
from nti.analytics.database.enrollments import CourseEnrollments
from nti.analytics.database.enrollments import CourseDrops

from nti.analytics.tests import NTIAnalyticsTestCase
from nti.analytics.tests import TestIdentifier

class TestEnrollments( NTIAnalyticsTestCase ):

	def setUp(self):
		self.db = AnalyticsDB( dburi='sqlite://' )
		component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
		self.session = self.db.session
		self.patches = [
			patch_object( identifier.SessionId, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier._DSIdentifier, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier._NtiidIdentifier, 'get_id', TestIdentifier.get_id ) ]

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.db, provided=IAnalyticsDB )
		self.session.close()

		for patch in self.patches:
			patch.restore()

	@WithMockDSTrans
	def test_enrollments(self):
		principal = User.create_user( username='sjohnson@nextthought.com', dataserver=self.ds )
		self.ds.root[principal.id] = principal
		admin = courses.CourseAdministrativeLevel()
		self.ds.root['admin'] = admin
		course = courses.CourseInstance()
		admin['course'] = course
		self.section = course.SubInstances['section1'] = courses.ContentCourseSubInstance()
		self.principal  = principal
		self.course = course

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


