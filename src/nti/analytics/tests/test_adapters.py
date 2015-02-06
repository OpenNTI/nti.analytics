#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
from hamcrest.library.collection.issequence_containinginanyorder import contains_inanyorder
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time
import fudge
from fudge import patch_object

from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import none
from hamcrest import has_length

from datetime import datetime

from zope import component

from nti.app.products.courseware.interfaces import IViewCount

from nti.contenttypes.courses.courses import CourseInstance

from nti.dataserver.users.users import User
from nti.dataserver.contenttypes.note import Note
from nti.dataserver.contenttypes.forums.topic import Topic

from nti.analytics import identifier

from nti.analytics.database import get_analytics_db
from nti.analytics.database import boards as db_boards_view
from nti.analytics.database import resource_tags as db_tags_view
from nti.analytics.database.root_context import _create_course
from nti.analytics.database.users import create_user
from nti.analytics.database.assessments import AssignmentsTaken
from nti.analytics.database.assessments import SelfAssessmentsTaken

from nti.analytics.interfaces import IProgress

from nti.analytics.progress import get_assessment_progresses_for_course

from nti.assessment.assignment import QAssignment
from nti.assessment.question import QQuestionSet

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.tests import TestIdentifier
from nti.analytics.tests import NTIAnalyticsTestCase

from nti.testing.time import time_monotonically_increases

def _create_topic_view( user_id, topic ):
	time_length = 30
	event_time = time.time()
	db_boards_view.create_topic_view( user_id, None, event_time,
									1, None, topic, time_length )

def _create_note_view( user_id, note ):
	event_time = time.time()
	db_tags_view.create_note_view( user_id, None, event_time,
									None, 1, note )

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
		course_id = 1
		new_course = CourseInstance()
		setattr( new_course, '_ds_intid', course_id )
		_create_course( self.analytics_db, new_course, course_id )
		return new_course

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
		"Test progress for assessment adapters and courses."
		mock_validate.is_callable().returns( True )

		user = self._install_user()
		course = self._install_course()
		assignment = self._get_assignment()
		question_set = self._get_self_assessment()

		# No initial progress for assessments
		result = component.queryMultiAdapter( (user, assignment), IProgress )
		assert_that( result, none() )

		result = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( result, none() )

		# Install assignment
		self._install_assignment( self.analytics_db )
		assignment_progress = component.queryMultiAdapter( (user, assignment), IProgress )
		assert_that( assignment_progress, not_none() )
		assert_that( assignment_progress.HasProgress, is_( True ))

		result = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( result, none() )

		# Verify progress for course
		progressess = get_assessment_progresses_for_course( user, course )
		assert_that( progressess, has_length( 1 ) )
		assert_that( progressess[0], is_( assignment_progress ) )

		# Self-assessment
		self._install_self_assessment( self.analytics_db )
		result = component.queryMultiAdapter( (user, assignment), IProgress )
		assert_that( result, not_none() )
		assert_that( result.HasProgress, is_( True ))

		assessment_progress = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( assessment_progress, not_none() )
		assert_that( assessment_progress.HasProgress, is_( True ))

		# Verify progress course w/one of each
		# Assignment progress is unchanged.
		progressess = get_assessment_progresses_for_course( user, course )
		assert_that( progressess, has_length( 2 ) )
		assert_that( progressess,
					contains_inanyorder( assessment_progress, assignment_progress ) )

		# Self-assessment; duped is ok
		self._install_self_assessment( self.analytics_db, submit_id=100 )
		assessment_progress = component.queryMultiAdapter( (user, question_set), IProgress )
		assert_that( assessment_progress, not_none() )
		assert_that( assessment_progress.HasProgress, is_( True ))

		# Verify progress course w/one of each plus multi-assessments
		# The new self-assessment timestamp is in our progress.
		progressess = get_assessment_progresses_for_course( user, course )
		assert_that( progressess, has_length( 2 ) )
		assert_that( progressess,
					contains_inanyorder( assessment_progress, assignment_progress ) )

class TestViewCountAdapters( NTIAnalyticsTestCase ):

	def setUp(self):
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

	@time_monotonically_increases
	def test_topic_view_counts(self):
		topic = Topic()
		result = IViewCount( topic )
		assert_that( result, is_( 0 ))

		_create_topic_view( 1, topic )
		result = IViewCount( topic )
		assert_that( result, is_( 1 ))

		topic_view_count = 5
		for _ in range( topic_view_count ):
			_create_topic_view( 1, topic )

		result = IViewCount( topic )
		assert_that( result, is_( topic_view_count + 1 ))

	@time_monotonically_increases
	def test_note_view_counts(self):
		note = Note()
		note.body = ('test',)
		result = IViewCount( note )
		assert_that( result, is_( 0 ))

		_create_note_view( 1, note )
		result = IViewCount( note )
		assert_that( result, is_( 1 ))

		note_view_count = 5
		for _ in range( note_view_count ):
			_create_note_view( 1, note )

		result = IViewCount( note )
		assert_that( result, is_( note_view_count + 1 ))

