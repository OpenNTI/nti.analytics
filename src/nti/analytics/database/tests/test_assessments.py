#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

from nti.analytics.database.tests import AnalyticsTestBase

from nti.analytics.database import assessments as db_assessments

from nti.analytics.database.assessments import _get_grade
from nti.analytics.database.assessments import AssignmentsTaken
from nti.analytics.database.assessments import AssignmentDetails
from nti.analytics.database.assessments import AssignmentGrades
from nti.analytics.database.assessments import AssignmentDetailGrades
from nti.analytics.database.assessments import SelfAssessmentsTaken

class TestAssessments(AnalyticsTestBase):

	def test_grade(self):
		# Could be a lot of types: 7, 7/10, 95, 95%, A-, 90 A
		grade_num = _get_grade( 100 )
		assert_that( grade_num, is_( 100 ) )

		grade_num = _get_grade( 98.6 )
		assert_that( grade_num, is_( 98.6 ) )

		grade_num = _get_grade( '98 -' )
		assert_that( grade_num, is_( 98 ) )

		# We don't handle this yet.
		grade_num = _get_grade( '90 A' )
		assert_that( grade_num, none() )

