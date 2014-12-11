#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import none

from datetime import datetime

from zope import component

import fudge
from fudge import patch_object

from nti.dataserver.users.users import User

from nti.analytics import identifier

from nti.analytics.database import get_analytics_db
from nti.analytics.database.root_context import _create_course
from nti.analytics.database.users import create_user
from nti.analytics.database.assessments import AssignmentsTaken
from nti.analytics.database.assessments import SelfAssessmentsTaken

from nti.analytics.interfaces import IProgress

from nti.assessment.assignment import QAssignment
from nti.assessment.question import QQuestionSet

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.tests import TestIdentifier
from nti.analytics.tests import NTIAnalyticsTestCase

class TestAnalyticAdapters( NTIAnalyticsTestCase ):

	def setUp(self):
		self.analytics_db = get_analytics_db()

		self.patches = [
			patch_object( identifier.RootContextId, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier._DSIdentifier, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier._NtiidIdentifier, 'get_id', TestIdentifier.get_id ),
			patch_object( identifier.RootContextId, 'get_object', TestIdentifier.get_object ),
			patch_object( identifier._DSIdentifier, 'get_object', TestIdentifier.get_object ),
			patch_object( identifier._NtiidIdentifier, 'get_object', TestIdentifier.get_object ) ]

	def tearDown(self):
		for patch in self.patches:
			patch.restore()

	def _get_assignment(self):
		new_assignment = QAssignment()
		new_assignment.ntiid = self.assignment_id = 'tag:ntiid1'
		return new_assignment

	def _get_self_assessment(self):
		assessment = QQuestionSet()
		assessment.ntiid = self.question_set_id = 'tag:question_set1'
		return assessment

	def _install_user(self):
		self.user = User.create_user( username='derpity', dataserver=self.ds )
		self.user_id = create_user( self.user ).user_id
		return self.user

	def _install_course(self):
		_create_course( self.analytics_db, 1, 1 )

	def _install_assignment(self, db):
		new_object = AssignmentsTaken( 	user_id=self.user_id,
									session_id=2,
									timestamp=datetime.utcnow(),
									course_id=1,
									assignment_id=self.assignment_id,
									submission_id=2,
									time_length=10 )
		db.session.add( new_object )
		db.session.flush()

	def _install_self_assessment(self, db, submit_id=1 ):
		new_object = SelfAssessmentsTaken( 	user_id=self.user_id,
										session_id=2,
										timestamp=datetime.utcnow(),
										course_id=1,
										assignment_id=self.question_set_id,
										submission_id=submit_id,
										time_length=10 )
		db.session.add( new_object )
		db.session.flush()

	@WithMockDSTrans
	@fudge.patch( 'dm.zope.schema.schema.Object._validate' )
	def test_progress_adapter(self, mock_validate):
		mock_validate.is_callable().returns( True )
		user = self._install_user()
		self._install_course()
		assignment = self._get_assignment()
		question_set = self._get_self_assessment()

		# No initial progress for assessments
		result = component.queryMultiAdapter( (user, assignment), IProgress )
		assert_that( result, none() )

		result = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( result, none() )

		# Install assignment
		self._install_assignment( self.analytics_db )
		result = component.queryMultiAdapter( (user, assignment), IProgress )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ))

		result = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( result, none() )

		# Self-assessment
		self._install_self_assessment( self.analytics_db )
		result = component.queryMultiAdapter( (user, assignment), IProgress )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ))

		result = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ))

		# Self-assessment; duped is ok
		self._install_self_assessment( self.analytics_db, submit_id=100 )
		result = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ))



