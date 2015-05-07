#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import fudge
import time
import weakref

from datetime import datetime
from datetime import timedelta

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that
from hamcrest import not_none
from hamcrest import has_length

from zope.interface import directlyProvides

from nti.app.assessment.feedback import UsersCourseAssignmentHistoryItemFeedback
from nti.app.assessment.history import UsersCourseAssignmentHistory
from nti.contenttypes.courses.courses import CourseInstance

from nti.assessment.assessed import QAssessedQuestionSet
from nti.assessment.assessed import QAssessedQuestion
from nti.assessment.assessed import QAssessedPart
from nti.assessment.assignment import QAssignment
from nti.assessment.assignment import QAssignmentSubmissionPendingAssessment
from nti.assessment.submission import AssignmentSubmission
from nti.assessment.submission import QuestionSetSubmission
from nti.assessment.submission import QuestionSubmission

from nti.app.products.gradebook.grades import Grade

from nti.analytics.database.tests import test_user_ds_id
from nti.analytics.database.tests import test_session_id
from nti.analytics.database.tests import AnalyticsTestBase
from nti.analytics.database.tests import NTIAnalyticsTestCase

from nti.analytics.database import assessments as db_assessments
from nti.analytics.database import get_analytics_db

from nti.analytics.database.assessments import _get_grade_val
from nti.analytics.database.assessments import _get_response
from nti.analytics.database.assessments import _load_response
from nti.analytics.database.assessments import AssignmentsTaken
from nti.analytics.database.assessments import AssignmentViews
from nti.analytics.database.assessments import SelfAssessmentViews
from nti.analytics.database.assessments import AssignmentDetails
from nti.analytics.database.assessments import AssignmentGrades
from nti.analytics.database.assessments import AssignmentFeedback
from nti.analytics.database.assessments import AssignmentDetailGrades
from nti.analytics.database.assessments import SelfAssessmentsTaken
from nti.analytics.database.assessments import SelfAssessmentDetails

from nti.dataserver.interfaces import IUser
from nti.dataserver.users.users import Principal

_question_id = '1968'
_question_set_id = '2'
_assignment_id = 'b'
_response = 'bleh'

def _get_assessed_question_set():
	assessed_parts = []
	assessed = []
	assessed_parts.append( QAssessedPart(submittedResponse=_response, assessedValue=1.0))
	assessed.append( QAssessedQuestion(questionId=_question_id, parts=assessed_parts) )

	return QAssessedQuestionSet(questionSetId=_question_set_id, questions=assessed)

def _get_history_item():
	question_set = _get_assessed_question_set()
	history = UsersCourseAssignmentHistory()
	qs_submission = QuestionSetSubmission(
						questionSetId=_question_set_id,
						questions=(QuestionSubmission(questionId=_question_id, parts=(_response,)),))
	submission = AssignmentSubmission(assignmentId=_assignment_id, parts=(qs_submission,))
	pending = QAssignmentSubmissionPendingAssessment( assignmentId=_assignment_id,
													   parts=(question_set,) )
	result = history.recordSubmission( submission, pending )

	# Need a weak ref for owner.
	result_creator = Principal( username=str( test_user_ds_id ) )
	directlyProvides( result_creator, IUser )
	result_creator.__dict__['_ds_intid'] = test_user_ds_id
	history.owner = weakref.ref( result_creator )

	result.createdTime = time.time()
	result.Assignment = QAssignment( parts=() )
	return result, result_creator

class TestAssessments(AnalyticsTestBase):

	def setUp(self):
		super( TestAssessments, self ).setUp()

	def test_assessments(self):
		sa_records = db_assessments.get_self_assessments_for_user( test_user_ds_id, self.course_id )
		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 0 ) )
		sa_records = db_assessments.get_self_assessments_for_course( self.course_id )
		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 0 ))
		sa_details = self.db.session.query( SelfAssessmentDetails ).all()
		assert_that( sa_details, has_length( 0 ))

		new_assessment = _get_assessed_question_set()
		db_assessments.create_self_assessment_taken(
								test_user_ds_id, test_session_id, datetime.now(), self.course_id, new_assessment )

		# By course/user
		sa_records = db_assessments.get_self_assessments_for_user( test_user_ds_id, self.course_id )
		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 1 ))

		sa_taken = sa_records[0]
		assert_that( sa_taken.Submission, is_( new_assessment ))
		assert_that( sa_taken.timestamp, not_none() )

		# By course
		sa_records = db_assessments.get_self_assessments_for_course( self.course_id )
		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 1 ))

		sa_taken = sa_records[0]
		assert_that( sa_taken.Submission, is_( new_assessment ))
		assert_that( sa_taken.timestamp, not_none() )

		# DB
		sa_records = self.db.session.query( SelfAssessmentsTaken ).all()
		assert_that( sa_records, has_length( 1 ))

		sa_taken = sa_records[0]
		assert_that( sa_taken.user_id, is_( 1 ))
		assert_that( sa_taken.course_id, is_( 1 ))
		assert_that( sa_taken.timestamp, not_none() )
		assert_that( sa_taken.time_length, is_( -1 ) )
		assert_that( sa_taken.assignment_id, is_( '2' ) )
		assert_that( sa_taken.submission_id, is_( 101 ) )

		# Details
		sa_details = self.db.session.query( SelfAssessmentDetails ).all()
		assert_that( sa_details, has_length( 1 ))

		sa_detail = sa_details[0]
		assert_that( sa_detail.user_id, is_( 1 ))
		assert_that( sa_detail.timestamp, not_none() )
		assert_that( sa_detail.time_length, is_( -1 ) )
		assert_that( sa_detail.submission, is_( '"bleh"' ) )
		assert_that( sa_detail.self_assessment_id, is_( 1 ) )
		assert_that( sa_detail.question_id, is_( '1968' ) )
		assert_that( sa_detail.question_part_id, is_( 0 ) )

	def test_idempotent(self):
		sa_records = db_assessments.get_self_assessments_for_user( test_user_ds_id, self.course_id )
		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 0 ) )

		assessment_time = datetime.now()
		new_assessment = _get_assessed_question_set()
		db_assessments.create_self_assessment_taken(
								test_user_ds_id, test_session_id, assessment_time, self.course_id, new_assessment )

		sa_records = db_assessments.get_self_assessments_for_user( test_user_ds_id, self.course_id )
		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 1 ) )

		# Again
		db_assessments.create_self_assessment_taken(
								test_user_ds_id, test_session_id, assessment_time, self.course_id, new_assessment )

		sa_records = [x for x in sa_records]
		assert_that( sa_records, has_length( 1 ) )

class TestAssignments(NTIAnalyticsTestCase):

	def setUp(self):
		super( TestAssignments, self ).setUp()
		self.course = CourseInstance()
		self.course.__dict__['_ds_intid'] = 1111
		self.db = get_analytics_db()
		self.course_id = 2

	def test_grade(self):
		# Could be a lot of types: 7, 7/10, 95, 95%, A-, 90 A
		grade_num = _get_grade_val( 100 )
		assert_that( grade_num, is_( 100 ) )

		grade_num = _get_grade_val( '20' )
		assert_that( grade_num, is_( 20 ) )

		grade_num = _get_grade_val( 98.6 )
		assert_that( grade_num, is_( 98.6 ) )

		grade_num = _get_grade_val( '98 -' )
		assert_that( grade_num, is_( 98 ) )

		# We don't handle this yet.
		grade_num = _get_grade_val( '90 A' )
		assert_that( grade_num, none() )

	def __get_response(self, answer):
		# No user or question part needed unless we're testing randomized.
		return _get_response( None, None, answer )

	def test_answer(self):
		answer = 'booya'
		answer1 = _load_response( self.__get_response( answer ))
		assert_that( answer1, is_( answer ))

		answer = 1984
		answer1 = _load_response( self.__get_response( answer ))
		assert_that( answer1, is_( answer ))

		answer = [10, 9, 8, 7]
		answer1 = _load_response( self.__get_response( answer ))
		assert_that( answer1, is_( answer ))

		answer = {1:2, 3:4, 9:10}
		answer1 = _load_response( self.__get_response( answer ))
		assert_that( answer1, is_( answer ))

		# We don't handle mixed key types.
		answer = {'1':2, '3':4, 'why':10, 'how':18}
		answer1 = _load_response( self.__get_response( answer ))
		assert_that( answer1, is_( answer ))

	def test_assignments(self):
		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 0 ) )
		assignment_records = db_assessments.get_assignments_for_course( self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 0 ))
		assignment_details = self.db.session.query( AssignmentDetails ).all()
		assert_that( assignment_details, has_length( 0 ))
		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 0 ))
		assignment_grades = self.db.session.query( AssignmentGrades ).all()
		assert_that( assignment_grades, has_length( 0 ))

		# Submit assignment w/no grade
		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 0 ) )

		new_assignment, _ = _get_history_item()
		now = datetime.utcnow()
		db_assessments.create_assignment_taken(
								test_user_ds_id, test_session_id, now, self.course, new_assignment )

		# Check grade
		assignment_grades = self.db.session.query( AssignmentGrades ).all()
		assert_that( assignment_grades, has_length( 0 ))
		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 0 ))

		# By course/user
		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ))
		assert_that( assignment_records[0].IsLate, is_( False ))

		assignment_taken = assignment_records[0]
		assert_that( assignment_taken.Submission, is_( new_assignment ))
		assert_that( assignment_taken.timestamp, not_none() )

		# By course
		assignment_records = db_assessments.get_assignments_for_course( self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ))

		assignment_taken = assignment_records[0]
		assert_that( assignment_taken.Submission, is_( new_assignment ))
		assert_that( assignment_taken.timestamp, not_none() )
		assert_that( assignment_taken.Grade, none() )

		# DB
		assignment_records = self.db.session.query( AssignmentsTaken ).all()
		assert_that( assignment_records, has_length( 1 ))

		assignment_taken = assignment_records[0]
		assert_that( assignment_taken.user_id, is_( 1 ))
		assert_that( assignment_taken.course_id, is_( self.course_id ))
		assert_that( assignment_taken.timestamp, not_none() )
		assert_that( assignment_taken.time_length, is_( -1 ) )
		assert_that( assignment_taken.assignment_id, is_( 'b' ) )

		# Details
		assignment_details = self.db.session.query( AssignmentDetails ).all()
		assert_that( assignment_details, has_length( 1 ))

		assignment_detail = assignment_details[0]
		assert_that( assignment_detail.user_id, is_( 1 ))
		assert_that( assignment_detail.timestamp, not_none() )
		assert_that( assignment_detail.time_length, is_( -1 ) )
		assert_that( assignment_detail.submission, is_( '"bleh"' ) )
		assert_that( assignment_detail.assignment_taken_id, is_( 1 ) )
		assert_that( assignment_detail.question_id, is_( '1968' ) )
		assert_that( assignment_detail.question_part_id, is_( 0 ) )

	@fudge.patch( 'nti.analytics.database.assessments._get_grade' )
	def test_assignment_with_grade(self, mock_get_grade):
		my_grade = Grade( grade='20' )
		mock_get_grade.is_callable().returns( my_grade )

		# Submit assignment w/no grade
		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 0 ) )

		new_assignment, _ = _get_history_item()
		now = datetime.utcnow()
		month_ago = now - timedelta( days=30 )
		new_assignment.Assignment.available_for_submission_ending = month_ago
		db_assessments.create_assignment_taken(
								test_user_ds_id, test_session_id, now, self.course, new_assignment )

		# Check grade
		assignment_grades = self.db.session.query( AssignmentGrades ).all()
		assert_that( assignment_grades, has_length( 1 ))
		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 0 ))

		# By course/user
		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ))
		assert_that( assignment_records[0].IsLate, is_( True ))

		assignment_taken = assignment_records[0]
		assert_that( assignment_taken.Submission, is_( new_assignment ))
		assert_that( assignment_taken.timestamp, not_none() )
		assert_that( assignment_taken.Grade, is_( '20' ) )
		assert_that( assignment_taken.GradeNum, is_( 20 ) )

		# By course
		assignment_records = db_assessments.get_assignments_for_course( self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ))

		assignment_taken = assignment_records[0]
		assert_that( assignment_taken.Submission, is_( new_assignment ))
		assert_that( assignment_taken.timestamp, not_none() )

		# Details
		assignment_taken= db_assessments.get_assignment_details_for_course( self.course, _assignment_id)
		assignment_taken = [x for x in assignment_taken]
		assert_that( assignment_taken, has_length( 1 ))

		assignment_details = assignment_taken[0].Details
		assignment_details = [x for x in assignment_details]
		assert_that( assignment_details, has_length( 1 ))

		assignment_detail = assignment_details[0]
		assert_that( assignment_detail.IsCorrect, is_( 1 ))
		assert_that( assignment_detail.Grade, is_( '1.0' ))

		# DB
		assignment_details = self.db.session.query( AssignmentDetails ).all()
		assert_that( assignment_details, has_length( 1 ))

		assignment_detail = assignment_details[0]
		assert_that( assignment_detail.user_id, is_( 1 ))
		assert_that( assignment_detail.timestamp, not_none() )
		assert_that( assignment_detail.time_length, is_( -1 ) )
		assert_that( assignment_detail.submission, is_( '"bleh"' ) )
		assert_that( assignment_detail.assignment_taken_id, is_( 1 ) )
		assert_that( assignment_detail.question_id, is_( '1968' ) )
		assert_that( assignment_detail.question_part_id, is_( 0 ) )

		assignment_details = self.db.session.query( AssignmentDetailGrades ).all()
		assert_that( assignment_details, has_length( 1 ))

		assignment_detail = assignment_details[0]
		assert_that( assignment_detail.user_id, is_( 1 ))
		assert_that( assignment_detail.timestamp, not_none() )
		assert_that( assignment_detail.assignment_taken_id, is_( 1 ) )
		assert_that( assignment_detail.question_id, is_( '1968' ) )
		assert_that( assignment_detail.question_part_id, is_( 0 ) )
		assert_that( assignment_detail.is_correct, is_( 1 ) )
		assert_that( assignment_detail.grade, is_( '1.0' ) )

	@fudge.patch( 'nti.analytics.database.assessments._get_grade_id' )
	def test_feedback(self, mock_get_grade):
		grade_id = 1
		mock_get_grade.is_callable().returns( grade_id )

		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 0 ))

		# Create object
		new_assignment, _ = _get_history_item()
		feedback = UsersCourseAssignmentHistoryItemFeedback()
		feedback.creator = feedback_creator = '9999'
		feedback.__dict__['body'] = feedback_body = 'blehblehbleh'
		feedback.__parent__ = new_assignment

		db_assessments.create_assignment_taken(
						test_user_ds_id, test_session_id, datetime.now(), self.course, new_assignment )

		db_assessments.create_submission_feedback(
						feedback_creator, test_session_id, datetime.now(), new_assignment, feedback )

		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 1 ))

		feedback_record = assignment_feedback[0]
		assert_that( feedback_record.user_id, is_( 2 ))
		assert_that( feedback_record.timestamp, not_none() )
		assert_that( feedback_record.assignment_taken_id, is_( 1 ) )
		assert_that( feedback_record.feedback_ds_id, not_none() )
		assert_that( feedback_record.feedback_length, is_( len( feedback_body ) ) )
		assert_that( feedback_record.grade_id, is_( grade_id ) )

	@fudge.patch( 'nti.analytics.database.assessments._get_grade_id' )
	def test_feedback_lazy_creates_assignment_record(self, mock_get_grade):
		grade_id = 1
		mock_get_grade.is_callable().returns( grade_id )

		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 0 ))

		# Create object
		new_assignment, result_creator = _get_history_item()
		course = self.course
		new_assignment.__parent__.__parent__ = course
		feedback = UsersCourseAssignmentHistoryItemFeedback()
		feedback.__dict__['creator'] = feedback_creator = Principal( username='9999' )
		feedback_creator.__dict__['_ds_intid'] = 9999
		feedback.__dict__['body'] = 'blehblehbleh'
		feedback.__parent__ = new_assignment

		# Create feedback without assignment record
		db_assessments.create_submission_feedback(
						feedback_creator, test_session_id, datetime.now(), new_assignment, feedback )

		assignment_feedback = self.db.session.query( AssignmentFeedback ).all()
		assert_that( assignment_feedback, has_length( 1 ))

		# By course/user
		assignment_records = db_assessments.get_assignments_for_user(
										result_creator,
										course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ))

		# Assignments created
		assignment_records = db_assessments.get_assignments_for_course( course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ))


	def test_idempotent(self):
		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 0 ) )

		assignment_time = datetime.now()
		new_assignment, _ = _get_history_item()
		db_assessments.create_assignment_taken(
					test_user_ds_id, test_session_id, assignment_time, self.course, new_assignment )

		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ) )

		# Again
		db_assessments.create_assignment_taken(
					test_user_ds_id, test_session_id, assignment_time, self.course, new_assignment )

		assignment_records = db_assessments.get_assignments_for_user( test_user_ds_id, self.course )
		assignment_records = [x for x in assignment_records]
		assert_that( assignment_records, has_length( 1 ) )

	def test_assessment_views(self):
		results = self.db.session.query( SelfAssessmentViews ).all()
		assert_that( results, has_length( 0 ))
		results = self.db.session.query( AssignmentViews ).all()
		assert_that( results, has_length( 0 ))

		resource = None
		context_path_flat = 'dashboard'
		context_path= [ 'dashboard' ]
		time_length = 30
		event_time = time.time()
		question_set_id = 'tag:nextthought.com,2011-10:OU-NAQ-CLC3403_LawAndJustice.naq.set.qset:QUIZ1_aristotle'
		assignment_id = 'tag:nextthought.com,2011-10:OU-HTML-CLC3403_LawAndJustice.sec:QUIZ_01.01'

		db_assessments.create_self_assessment_view( test_user_ds_id, test_session_id, event_time,
												self.course_id, context_path, resource, time_length, question_set_id )

		results = self.db.session.query( SelfAssessmentViews ).all()
		assert_that( results, has_length( 1 ))
		resource_view = results[0]
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( context_path_flat ) )
		assert_that( resource_view.resource_id, none() )
		assert_that( resource_view.time_length, is_( time_length ) )
		assert_that( resource_view.assignment_id, is_( question_set_id ) )

		db_assessments.create_assignment_view( test_user_ds_id, test_session_id, event_time,
											self.course_id, context_path, resource, time_length, assignment_id )

		results = self.db.session.query( AssignmentViews ).all()
		assert_that( results, has_length( 1 ))
		resource_view = results[0]
		assert_that( resource_view.user_id, is_( 1 ) )
		assert_that( resource_view.session_id, is_( test_session_id ) )
		assert_that( resource_view.timestamp, not_none() )
		assert_that( resource_view.course_id, is_( self.course_id ) )
		assert_that( resource_view.context_path, is_( context_path_flat ) )
		assert_that( resource_view.resource_id, none() )
		assert_that( resource_view.time_length, is_( time_length ) )
		assert_that( resource_view.assignment_id, is_( assignment_id ) )

		# Test idempotent; nothing added
		db_assessments.create_self_assessment_view( test_user_ds_id, test_session_id, event_time,
												self.course_id, context_path, resource, time_length, question_set_id )

		results = self.db.session.query( SelfAssessmentViews ).all()
		assert_that( results, has_length( 1 ))

		db_assessments.create_assignment_view( test_user_ds_id, test_session_id, event_time,
											self.course_id, context_path, resource, time_length, assignment_id )

		results = self.db.session.query( AssignmentViews ).all()
		assert_that( results, has_length( 1 ))

		# With resource
		event_time = event_time + 1
		resource = 'ntiid:bleh_page1'
		db_assessments.create_self_assessment_view( test_user_ds_id, test_session_id, event_time,
												self.course_id, context_path, resource, time_length, question_set_id )

		results = self.db.session.query( SelfAssessmentViews ).all()
		assert_that( results, has_length( 2 ))

		db_assessments.create_assignment_view( test_user_ds_id, test_session_id, event_time,
											self.course_id, context_path, resource, time_length, assignment_id )

		results = self.db.session.query( AssignmentViews ).all()
		assert_that( results, has_length( 2 ))
