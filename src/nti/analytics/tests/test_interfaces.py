#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.contenttypes.courses.courses import CourseInstance
from nti.contenttypes.courses.enrollment import DefaultCourseInstanceEnrollmentRecord

from nti.dataserver.users import User

from nti.testing.matchers import verifiably_provides

from ..interfaces import IAnalyticsContext

class TestAnalyticsContext( NTIAnalyticsTestCase ):
    """
    Tests that things that should be analytics context aware, are.
    """

    def test_user_is_context(self):
        user = User('testuser')
        assert_that(user, verifiably_provides(IAnalyticsContext))

    def test_course_is_context(self):
        course = CourseInstance()
        assert_that(course, verifiably_provides(IAnalyticsContext))

    def test_enrollment_record_is_context(self):
        enrollment = DefaultCourseInstanceEnrollmentRecord()
        assert_that(enrollment, verifiably_provides(IAnalyticsContext))


