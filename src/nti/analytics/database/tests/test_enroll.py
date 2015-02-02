#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from datetime import datetime

from hamcrest import is_
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import MockParent
MockFL = MockNote = MockHighlight = MockTopic = MockComment = MockThought = MockForum = MockParent

from nti.analytics.database import enrollments as db_enrollments

from nti.analytics.database.enrollments import CourseCatalogViews
from nti.analytics.database.enrollments import EnrollmentTypes
from nti.analytics.database.enrollments import CourseEnrollments
from nti.analytics.database.enrollments import CourseDrops

class TestCourseViews(AnalyticsTestBase):

	def setUp(self):
		super( TestCourseViews, self ).setUp()

	def test_course_catalog_views(self):
		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 0 ) )
		context_path = None

		time_length = 30
		db_enrollments.create_course_catalog_view( test_user_ds_id, test_session_id, datetime.now(),
													context_path,
													self.course_id, time_length )

		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 1 ) )

		catalog_view = self.session.query( CourseCatalogViews ).one()
		assert_that( catalog_view.session_id, is_( test_session_id ) )
		assert_that( catalog_view.user_id, is_( 1 ) )
		assert_that( catalog_view.course_id, is_( self.course_id ) )
		assert_that( catalog_view.time_length, is_( time_length ) )
		assert_that( catalog_view.timestamp, not_none() )

	def test_enrollment(self):
		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 0 ) )
		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 0 ) )
		results = db_enrollments.get_enrollments_for_course( self.course_id )
		assert_that( results, has_length( 0 ) )

		for_credit = 'for_credit'
		db_enrollments.create_course_enrollment( test_user_ds_id, test_session_id,
												datetime.now(), self.course_id, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )
		results = db_enrollments.get_enrollments_for_course( self.course_id )
		assert_that( results, has_length( 1 ) )

		enrollment = self.session.query( CourseEnrollments ).one()
		assert_that( enrollment.session_id, is_( test_session_id ) )
		assert_that( enrollment.user_id, is_( 1 ) )
		assert_that( enrollment.course_id, is_( self.course_id ) )
		assert_that( enrollment.timestamp, not_none() )
		assert_that( enrollment.type_id, is_( 1 ) )

		# EnrollmentType
		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 1 ) )

		enrollment_type = self.session.query( EnrollmentTypes ).one()
		assert_that( enrollment_type.type_name, is_( for_credit ) )

		# Another enrollment
		db_enrollments.create_course_enrollment( test_user_ds_id + 1, test_session_id,
												datetime.now(), self.course_id, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 2 ) )
		results = db_enrollments.get_enrollments_for_course( self.course_id )
		assert_that( results, has_length( 2 ) )

		results = self.session.query( EnrollmentTypes ).all()
		assert_that( results, has_length( 1 ) )

		# Drop
		db_enrollments.create_course_drop( test_user_ds_id, test_session_id, datetime.now(), self.course_id )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )
		results = db_enrollments.get_enrollments_for_course( self.course_id )
		assert_that( results, has_length( 1 ) )

		results = self.session.query( CourseDrops ).all()
		assert_that( results, has_length( 1 ) )
		drop = self.session.query( CourseDrops ).one()
		assert_that( drop.session_id, is_( test_session_id ) )
		assert_that( drop.user_id, is_( 1 ) )
		assert_that( drop.course_id, is_( self.course_id ) )
		assert_that( drop.timestamp, not_none() )

	def test_idempotent(self):
		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 0 ) )

		for_credit = 'for_credit'
		event_time = datetime.now()
		db_enrollments.create_course_enrollment( test_user_ds_id, test_session_id,
												event_time, self.course_id, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )

		db_enrollments.create_course_enrollment( test_user_ds_id, test_session_id,
												event_time, self.course_id, for_credit )

		results = self.session.query( CourseEnrollments ).all()
		assert_that( results, has_length( 1 ) )

	def test_idempotent_views(self):
		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 0 ) )
		context_path = None

		event_time = datetime.now()
		time_length = 30
		db_enrollments.create_course_catalog_view( test_user_ds_id, test_session_id, event_time,
													context_path, self.course_id, time_length )

		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 1 ) )

		db_enrollments.create_course_catalog_view( test_user_ds_id, test_session_id, event_time,
													context_path, self.course_id, time_length )

		results = self.session.query( CourseCatalogViews ).all()
		assert_that( results, has_length( 1 ) )
