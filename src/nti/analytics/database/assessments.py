#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import json

import zope.intid

from six import string_types

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import Boolean
from sqlalchemy import Text
from sqlalchemy import DateTime

from sqlalchemy.schema import Sequence
from sqlalchemy.schema import PrimaryKeyConstraint

from sqlalchemy.ext.declarative import declared_attr

from nti.app.products.gradebook.interfaces import IGrade

from nti.assessment.interfaces import IQAssessedQuestionSet
from nti.assessment.interfaces import IQUploadedFile
from nti.assessment.interfaces import IQModeledContentResponse

from nti.analytics.common import timestamp_type
from nti.analytics.common import get_creator

from nti.analytics.database.users import get_or_create_user

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import CourseId
from nti.analytics.identifier import SubmissionId
from nti.analytics.identifier import QuestionSetId
from nti.analytics.identifier import FeedbackId
_sessionid = SessionId()
_courseid = CourseId()
_submissionid = SubmissionId()
_questionsetid = QuestionSetId()
_feedbackid = FeedbackId()

from nti.analytics.database import SESSION_COLUMN_TYPE
from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import CourseMixin
from nti.analytics.database.meta_mixins import DeletedMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

class AssignmentMixin(BaseTableMixin,CourseMixin,TimeLengthMixin):
	# Max length of 160 as of 8.1.14
	@declared_attr
	def assignment_id(cls):
		return Column('assignment_id', NTIID_COLUMN_TYPE, nullable=False, index=True )

class AssignmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'AssignmentsTaken'
	submission_id = Column('submission_id', Integer, unique=True, index=True, autoincrement=False )

	assignments_taken_id = Column('assignment_taken_id', Integer, Sequence( 'assignments_taken_seq' ), primary_key=True )

class AssignmentSubmissionMixin(BaseTableMixin):
	@declared_attr
	def submission_id(cls):
		return Column('submission_id', Integer, ForeignKey("AssignmentsTaken.submission_id"), nullable=False, index=True)


class DetailMixin(TimeLengthMixin):
	# TODO Can we rely on these parts/ids being integers?
	# Max length of 114 as of 8.1.14
	@declared_attr
	def question_id(cls):
		return Column('question_id', NTIID_COLUMN_TYPE, nullable=False, index=True)

	@declared_attr
	def question_part_id(cls):
		return Column('question_part_id', Integer, nullable=False, autoincrement=False, index=True )

	# TODO separate submissions by question types?
	@declared_attr
	def submission(cls):
		# Null if left blank
		return Column('submission', Text, nullable=True) #(Freeform|MapEntry|Index|List)

class GradeMixin(object):
	# Could be a lot of types: 7, 7/10, 95, 95%, A-, 90 A
	@declared_attr
	def grade(cls):
		return Column('grade', String(32), nullable=True )

	# For easy aggregation
	@declared_attr
	def grade_num(cls):
		return Column('grade_num', Float, nullable=True )

	# 'Null' for auto-graded parts.
	@declared_attr
	def grader(cls):
		return Column('grader', Integer, ForeignKey("Users.user_id"), nullable=True, index=True )

class GradeDetailMixin(GradeMixin):
	# For multiple choice types
	@declared_attr
	def is_correct(cls):
		return Column('is_correct', Boolean, nullable=True )

class AssignmentDetails(Base,DetailMixin,AssignmentSubmissionMixin):
	__tablename__ = 'AssignmentDetails'

	assignment_details_id = Column('assignment_details_id', Integer, Sequence( 'assignment_details_seq' ), primary_key=True )

class AssignmentGrades(Base,AssignmentSubmissionMixin,GradeMixin):
	__tablename__ = 'AssignmentGrades'
	grade_id = Column('grade_id', Integer, Sequence( 'assignment_grade_id_seq' ), primary_key=True, index=True )

class AssignmentDetailGrades(Base,GradeDetailMixin,AssignmentSubmissionMixin):
	__tablename__ = 'AssignmentDetailGrades'
	# We cannot use foreign keys since the parent key must be unique, and
	# we cannot have this as part of a primary key due to its size (mysql).
	question_id = Column('question_id', NTIID_COLUMN_TYPE, nullable=False)
	question_part_id = Column('question_part_id', Integer, nullable=True, autoincrement=False)

	assignment_detail_grades_id = Column('assignment_detail_grades_id', Integer, Sequence( 'assignment_detail_grades_seq' ), primary_key=True )


# Each feedback 'tree' should have an associated grade with it.
class AssignmentFeedback(Base,AssignmentSubmissionMixin,DeletedMixin):
	__tablename__ = 'AssignmentFeedback'
	feedback_id = Column( 'feedback_id', Integer, nullable=False, unique=True, primary_key=True )
	feedback_length = Column( 'feedback_length', Integer, nullable=True )
	# Tie our feedback to our submission and grader.
	grade_id = Column('grade_id', Integer, ForeignKey("AssignmentGrades.grade_id"), nullable=False )

class SelfAssessmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'SelfAssessmentsTaken'
	submission_id = Column('submission_id', Integer, unique=True, primary_key=True, index=True, autoincrement=False )


# SelfAssessments will not have feedback or multiple graders
class SelfAssessmentDetails(Base,BaseTableMixin,DetailMixin,GradeDetailMixin):
 	__tablename__ = 'SelfAssessmentDetails'
 	submission_id = Column('submission_id', Integer, ForeignKey("SelfAssessmentsTaken.submission_id"), nullable=False, index=True)

	self_assessment_details_id = Column('self_assessment_details_id', Integer, Sequence( 'self_assessment_details_seq' ), primary_key=True )

def _get_duration( submission ):
	"""
	For a submission, retrieves how long it took to submit the object, in integer seconds.
	'-1' is returned if unknown.
	"""
	time_length = getattr( submission, 'CreatorRecordedEffortDuration', -1 )
	time_length = time_length or -1
	return int( time_length )

def _get_response(part):
	if IQUploadedFile.providedBy( part ):
		part = '<FILE_UPLOADED>'
	elif IQModeledContentResponse.providedBy( part ):
		part = ''.join( part.value )

	result = ''
	try:
		# Hmm, json will convert the keys to string as we dump them.  We
		# could try to handle that, or we could serialize differently.
		# I think, most importantly, we need to compare responses between users
		# (which this will handle) and to know if the answer was correct.
		# We may be fine as-is with json.
		result = json.dumps( part )
	except TypeError:
		logger.exception( 'Submission response is not serializable (type=%s)', type( part ) )

	return result

def _get_grade( grade_value ):
	# Convert the webapp's "number - letter" scheme to a number, or None.
	result = None
	if grade_value and isinstance(grade_value, string_types) and grade_value.endswith(' -'):
		try:
			result = float(grade_value.split()[0])
		except ValueError:
			pass
	return result

def create_self_assessment_taken(user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )
	submission_id = _submissionid.get_id( submission )
	self_assessment_id = _questionsetid.get_id( submission.questionSetId )
	# We likely will not have a grader.
	grader = _get_grader_id( db, submission )
	# TODO As a QAssessedQuestionSet. we will not have a duration.
	# I don't believe the submission was saved; so we cannot get it back.
	# We'd have to transfer it during adaptation perhaps.
	time_length = _get_duration( submission )

	new_object = SelfAssessmentsTaken( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										course_id=course_id,
										assignment_id=self_assessment_id,
										submission_id=submission_id,
										time_length=time_length )
	db.session.add( new_object )

	for assessed_question in submission.questions:
		question_id = assessed_question.questionId

		for idx, part in enumerate( assessed_question.parts ):
			grade = part.assessedValue
			is_correct = grade == 1
			response = _get_response( part.submittedResponse )
			grade_details = SelfAssessmentDetails( user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													submission_id=submission_id,
													question_id=question_id,
													question_part_id=idx,
													is_correct=is_correct,
													grade=grade,
													grader=grader,
													submission=response,
													time_length=time_length )
			db.session.add( grade_details )

def _get_grader_id( db, submission ):
	"""
	Returns a grader id for the submission if one exists (otherwise None).
	Currently, we have a one-to-one mapping between submission and grader.  That
	would need to change for things like peer grading.
	"""
	grader = None
	graded_submission = IGrade( submission, None )
	# If None, we're pending right?
	if graded_submission is not None:
		grader = get_creator( graded_submission )
		if grader is not None:
			grader = get_or_create_user(grader )
			grader = grader.user_id
	return grader

def create_assignment_taken(user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )
	submission_id = _submissionid.get_id( submission )
	assignment_id = submission.assignmentId
	submission_obj = submission.Submission
	time_length = _get_duration( submission_obj )

	new_object = AssignmentsTaken( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									assignment_id=assignment_id,
									submission_id=submission_id,
									time_length=time_length )
	db.session.add( new_object )

	# Submission Parts
	for set_submission in submission_obj.parts:
		for question_submission in set_submission.questions:
			# Questions don't have ds_intids, just use ntiid.
			question_id = question_submission.questionId
			# We'd like this by part, but will accept by question for now.
			time_length = _get_duration( question_submission )

			for idx, part in enumerate( question_submission.parts ):
				# Serialize our response
				response = _get_response( part )
				parts = AssignmentDetails( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											submission_id=submission_id,
											question_id=question_id,
											question_part_id=idx,
											submission=response,
											time_length=time_length )
				db.session.add( parts )

	# Grade
	graded_submission = IGrade( submission, None )
	# If None, we're pending right?
	if graded_submission is not None:
		grade = graded_submission.grade
		grade_num = _get_grade( grade )

		grader = _get_grader_id( db, submission )

		graded = AssignmentGrades( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									submission_id=submission_id,
									grade=grade,
									grade_num=grade_num,
									grader=grader )
		db.session.add( graded )

		# Submission Part Grades
		for maybe_assessed in submission.pendingAssessment.parts:
			if not IQAssessedQuestionSet.providedBy(maybe_assessed):
				# We're not auto-graded
				continue
			for assessed_question in maybe_assessed.questions:
				question_id = assessed_question.questionId

				for idx, part in enumerate( assessed_question.parts ):
					grade = part.assessedValue
					is_correct = grade == 1
					grade_details = AssignmentDetailGrades( user_id=uid,
															session_id=sid,
															timestamp=timestamp,
															submission_id=submission_id,
															question_id=question_id,
															question_part_id=idx,
															is_correct=is_correct,
															grade=grade,
															grader=grader )
					db.session.add( grade_details )

def grade_submission(user, nti_session, timestamp, grader, graded_val, submission ):
	db = get_analytics_db()
	grader = get_or_create_user(grader )
	grader_id  = grader.user_id
	submission_id = _submissionid.get_id( submission )
	grade_entry = _get_grade_entry( db, submission_id )
	timestamp = timestamp_type( timestamp )

	grade_num = _get_grade( graded_val )

	if grade_entry:
		# Update
		# If we wanted, we could just append every 'set_grade' action.
		grade_entry.grade = graded_val
		grade_entry.grade_num = grade_num
		grade_entry.timestamp = timestamp
		grade_entry.grader = grader_id
	else:
		# New grade
		user = get_or_create_user(user )
		uid = user.user_id
		sid = _sessionid.get_id( nti_session )

		new_object = AssignmentGrades( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										submission_id=submission_id,
										grade=graded_val,
										grade_num=grade_num,
										grader=grader_id )

		db.session.add( new_object )

def _get_grade_entry( db, submission_id ):
	# Currently, one assignment means one grade (and one grader).  If that changes, we'll
	# need to change this (at least)
	grade_entry = db.session.query(AssignmentGrades).filter(
												AssignmentGrades.submission_id==submission_id ).first()
	return grade_entry

def _get_grade_id( db, submission_id ):
	grade_entry = _get_grade_entry( db, submission_id )
	return grade_entry.grade_id

def create_submission_feedback( user, nti_session, timestamp, submission, feedback ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	timestamp = timestamp_type( timestamp )
	feedback_id = _feedbackid.get_id( feedback )
	feedback_length = sum( len( x ) for x in feedback.body )

	submission_id = _submissionid.get_id( submission )
	# TODO Do we need to handle any of these being None?
	# That's an error condition, right?
	grade_id = _get_grade_id( db, submission_id )

	new_object = AssignmentFeedback( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									submission_id=submission_id,
									feedback_id=feedback_id,
									feedback_length=feedback_length,
									grade_id=grade_id )
	db.session.add( new_object )

def delete_feedback( timestamp, feedback_id ):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	feedback = db.session.query(AssignmentFeedback).filter(
							AssignmentFeedback.feedback_id == feedback_id ).one()
	feedback.deleted=timestamp
	db.session.flush()

def get_self_assessments_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = _courseid.get_id( course )
	results = db.session.query(SelfAssessmentsTaken).filter( 	SelfAssessmentsTaken.user_id == uid,
																SelfAssessmentsTaken.course_id == course_id ).all()

	for sat in results:
		submission = _submissionid.get_object( sat.submission_id )
		setattr( sat, 'submission', submission )
	return results

def get_assignments_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = _courseid.get_id( course )
	results = db.session.query(AssignmentsTaken).filter( 	AssignmentsTaken.user_id == uid,
															AssignmentsTaken.course_id == course_id ).all()
	for at in results:
		submission = _submissionid.get_object( at.submission_id )
		setattr( at, 'submission', submission )
	return results

def get_self_assessments_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(SelfAssessmentsTaken).filter( SelfAssessmentsTaken.course_id == course_id ).all()

	for sat in results:
		submission = _submissionid.get_object( sat.submission_id )
		setattr( sat, 'submission', submission )
	return results

def get_assignments_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(AssignmentsTaken).filter( AssignmentsTaken.course_id == course_id ).all()
	return results

#AssignmentReport
def get_assignment_details_for_course(course):
	db = get_analytics_db()
	course_id = _courseid.get_id( course )
	results = db.session.query(AssignmentDetails).\
						join(AssignmentsTaken).\
						filter( AssignmentsTaken.course_id == course_id ).all()
	return results
