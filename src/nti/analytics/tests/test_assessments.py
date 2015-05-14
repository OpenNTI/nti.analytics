#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time
import fudge

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_length

from nti.dataserver.users import User

from nti.contenttypes.courses.courses import CourseInstance

from nti.analytics.assessments import get_assignment_views
from nti.analytics.assessments import get_self_assessment_views

from nti.analytics.model import SelfAssessmentViewEvent
from nti.analytics.model import AssignmentViewEvent

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import NTIAnalyticsTestCase

from ..resource_views import _add_self_assessment_event
from ..resource_views import _add_assignment_event

class TestAssessments( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_self_assess_event(self, mock_find_object):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		time_length = 120
		timestamp = time.time()
		question_set_id = 'tag:nextthought.com,2011-10:OU-NAQ-CLC3403_LawAndJustice.naq.set.qset:QUIZ1_aristotle'
		course = CourseInstance()
		mock_find_object.is_callable().returns( course )
		event = SelfAssessmentViewEvent( ResourceId=None,
										user=user.username,
										RootContextID='ntiid:fudge-lookup',
										context_path=None,
										Duration=time_length,
										timestamp=timestamp,
										QuestionSetId=question_set_id )

		results = get_self_assessment_views( user )
		assert_that( results, has_length( 0 ))

		# Can fetch
		_add_self_assessment_event( event )
		results = get_self_assessment_views( user )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user ))
		assert_that( results[0].Duration, is_( time_length ))
		assert_that( results[0].ResourceId, is_( question_set_id ))

		results = get_self_assessment_views( user, course=course )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user ))
		assert_that( results[0].Duration, is_( time_length ))
		assert_that( results[0].ResourceId, is_( question_set_id ))

		# Filtered out
		wrong_course = CourseInstance()
		wrong_course._ds_intid = 9999
		results = get_assignment_views( user, course=wrong_course )
		assert_that( results, has_length( 0 ))

	@WithMockDSTrans
	@fudge.patch( 'nti.ntiids.ntiids.find_object_with_ntiid' )
	def test_assignment_event(self, mock_find_object):
		user = User.create_user( username='new_user1', dataserver=self.ds )
		time_length = 120
		timestamp = time.time()
		assignment_id = 'tag:nextthought.com,2011-10:OU-NAQ-CLC3403_LawAndJustice.naq.set.qset:QUIZ1_aristotle'
		course = CourseInstance()
		course._ds_intid = 1111
		mock_find_object.is_callable().returns( course )
		event = AssignmentViewEvent( ResourceId=None,
									user=user.username,
									RootContextID='ntiid:fudge-lookup',
									context_path=None,
									Duration=time_length,
									timestamp=timestamp,
									AssignmentId=assignment_id )

		results = get_assignment_views( user )
		assert_that( results, has_length( 0 ))

		# Can fetch
		_add_assignment_event( event )
		results = get_assignment_views( user )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user ))
		assert_that( results[0].Duration, is_( time_length ))
		assert_that( results[0].ResourceId, is_( assignment_id ))

		results = get_assignment_views( user, course=course )
		assert_that( results, has_length( 1 ))
		assert_that( results[0].RootContext, is_( course ))
		assert_that( results[0].user, is_( user ))
		assert_that( results[0].Duration, is_( time_length ))
		assert_that( results[0].ResourceId, is_( assignment_id ))

		# Filtered out
		wrong_course = CourseInstance()
		wrong_course._ds_intid = 9999
		results = get_assignment_views( user, course=wrong_course )
		assert_that( results, has_length( 0 ))
