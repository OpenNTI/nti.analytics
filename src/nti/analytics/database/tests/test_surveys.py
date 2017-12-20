#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from nti.analytics_database.surveys import SurveyViews

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import NTIAnalyticsTestCase

from nti.analytics.database import surveys as db_surveys
from nti.analytics.database import get_analytics_db

from nti.contenttypes.courses.courses import CourseInstance


class TestSurveys(NTIAnalyticsTestCase):

	def setUp(self):
		super(TestSurveys, self).setUp()
		self.course = CourseInstance()
		self.course.__dict__['_ds_intid'] = 1111
		self.db = get_analytics_db()
		self.course_id = 2

	def test_survey_views(self):
		results = self.db.session.query(SurveyViews).all()
		assert_that( results, has_length( 0 ))

		resource = None
		context_path_flat = 'dashboard'
		context_path= ['dashboard']
		time_length = 30
		event_time = time.time()
		survey_id = 'tag:nextthought.com,2011-10:OU-NAQ-CLC3403_LawAndJustice.naq.set.qset:QUIZ1_aristotle'

		db_surveys.create_survey_view(test_user_ds_id, test_session_id,
									  event_time, self.course_id,
									  context_path, resource, time_length,
									  survey_id)

		results = self.db.session.query(SurveyViews).all()
		assert_that( results, has_length( 1 ))
		resource_view = results[0]
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( context_path_flat ) )
		assert_that( resource_view.resource_id, none() )
		assert_that( resource_view.time_length, is_(time_length ) )
		assert_that( resource_view.survey_id, is_(survey_id) )

		# Test idempotent; nothing added
		db_surveys.create_survey_view(test_user_ds_id, test_session_id,
									  event_time, self.course_id,
									  context_path, resource, time_length,
									  survey_id)

		results = self.db.session.query( SurveyViews ).all()
		assert_that( results, has_length( 1 ))

		# Update field
		db_surveys.create_survey_view(test_user_ds_id, test_session_id,
									  event_time, self.course_id,
									  context_path, resource, time_length * 2,
									  survey_id)

		results = self.db.session.query(SurveyViews).all()
		assert_that( results, has_length( 1 ))
		resource_view = results[0]
		assert_that( resource_view.time_length, is_(time_length * 2) )

		# With resource
		event_time = event_time + 1
		resource = 'ntiid:bleh_page1'
		db_surveys.create_survey_view(test_user_ds_id, test_session_id,
									  event_time, self.course_id,
									  context_path, resource, time_length,
									  survey_id)

		results = self.db.session.query(SurveyViews).all()
		assert_that(results, has_length(2))

		view_results = db_surveys.get_survey_views(test_user_ds_id)
		assert_that(view_results, has_length(2))
		assert_that(view_results, contains_inanyorder(*results))

