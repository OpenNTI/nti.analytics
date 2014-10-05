#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import json

from six import string_types
from six import integer_types

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import Boolean
from sqlalchemy import Text

from sqlalchemy.schema import Sequence
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import make_transient
from sqlalchemy.ext.declarative import declared_attr

from nti.app.products.gradebook.interfaces import IGrade

from nti.assessment.interfaces import IQAssessedQuestionSet
from nti.assessment.interfaces import IQUploadedFile
from nti.assessment.interfaces import IQModeledContentResponse

from nti.analytics.common import timestamp_type
from nti.analytics.common import get_creator

from nti.analytics.model import AnalyticsAssessment
from nti.analytics.model import AnalyticsAssignment
from nti.analytics.model import AnalyticsAssignmentDetail

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import SubmissionId
from nti.analytics.identifier import QuestionSetId
from nti.analytics.identifier import FeedbackId

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.users import get_user
from nti.analytics.database.courses import get_course_id
from nti.analytics.database.courses import get_course

from nti.analytics.database import resolve_objects
from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import INTID_COLUMN_TYPE
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
	submission_id = Column('submission_id', INTID_COLUMN_TYPE, nullable=True, index=True, autoincrement=False )

	assignment_taken_id = Column('assignment_taken_id', Integer, Sequence( 'assignments_taken_seq' ),
								index=True, nullable=False, primary_key=True )

	# We may have multiple grades in the future.
	grade = relationship( 'AssignmentGrades', uselist=False, lazy='joined' )

class AssignmentSubmissionMixin(BaseTableMixin):
	@declared_attr
	def assignment_taken_id(cls):
		return Column('assignment_taken_id', Integer, ForeignKey("AssignmentsTaken.assignment_taken_id"), nullable=False, index=True)


class DetailMixin(TimeLengthMixin):
	# Counting on these parts/ids being integers.
	# Max length of 114 as of 8.1.14
	@declared_attr
	def question_id(cls):
		return Column('question_id', NTIID_COLUMN_TYPE, nullable=False, index=True)

	@declared_attr
	def question_part_id(cls):
		return Column('question_part_id', INTID_COLUMN_TYPE, nullable=False, autoincrement=False, index=True )

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
	grade = relationship( 'AssignmentDetailGrades', uselist=False, lazy='joined' )

class AssignmentGrades(Base,AssignmentSubmissionMixin,GradeMixin):
	__tablename__ = 'AssignmentGrades'
	grade_id = Column('grade_id', Integer, Sequence( 'assignment_grade_id_seq' ), primary_key=True, index=True )

class AssignmentDetailGrades(Base,GradeDetailMixin,AssignmentSubmissionMixin):
	__tablename__ = 'AssignmentDetailGrades'
	# We cannot use foreign keys since the parent key must be unique, and
	# we cannot have this as part of a primary key due to its size (mysql).
	question_id = Column('question_id', NTIID_COLUMN_TYPE, nullable=False)
	question_part_id = Column('question_part_id', INTID_COLUMN_TYPE, nullable=True, autoincrement=False)

	assignment_details_id = Column('assignment_details_id', Integer, ForeignKey("AssignmentDetails.assignment_details_id"), unique=True, primary_key=True )


# Each feedback 'tree' should have an associated grade with it.
class AssignmentFeedback(Base,AssignmentSubmissionMixin,DeletedMixin):
	__tablename__ = 'AssignmentFeedback'
	feedback_ds_id = Column( 'feedback_ds_id', INTID_COLUMN_TYPE, nullable=True, unique=False )
	feedback_id = Column('feedback_id', Integer, Sequence( 'feedback_id_seq' ), primary_key=True )

	feedback_length = Column( 'feedback_length', Integer, nullable=True )
	# Tie our feedback to our submission and grader.
	grade_id = Column('grade_id', Integer, ForeignKey("AssignmentGrades.grade_id"), nullable=False )

class SelfAssessmentsTaken(Base,AssignmentMixin):
	__tablename__ = 'SelfAssessmentsTaken'
	submission_id = Column('submission_id', INTID_COLUMN_TYPE, nullable=True, index=True, autoincrement=False )
	self_assessment_id = Column('self_assessment_id', Integer, Sequence( 'self_assessment_seq' ),
								index=True, nullable=False, primary_key=True )


# SelfAssessments will not have feedback or multiple graders
class SelfAssessmentDetails(Base,BaseTableMixin,DetailMixin,GradeDetailMixin):
	__tablename__ = 'SelfAssessmentDetails'
	self_assessment_id = Column('self_assessment_id', Integer, ForeignKey("SelfAssessmentsTaken.self_assessment_id"), nullable=False, index=True)

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

def _load_response( value ):
	response = json.loads( value )
	if isinstance( response, dict ):
		# Map
		# Convert to int keys, if possible.
		# We currently do not handle mixed types of keys.
		try:
			response = {int( x ): y for x,y in response.items()}
		except ValueError:
			pass
	return response


def _get_grade_val( grade_value ):
	# Convert the webapp's "number - letter" scheme to a number, or None.
	result = None
	if grade_value and isinstance(grade_value, string_types):
		try:
			if grade_value.endswith(' -'):
				result = float(grade_value.split()[0])
			else:
				result = float(grade_value)
		except ValueError:
			pass
	elif grade_value and isinstance( grade_value, ( integer_types, float ) ):
		result = grade_value
	return result

def _get_self_assessment_id( db, submission_id ):
	self_assessment = db.session.query(SelfAssessmentsTaken).filter( SelfAssessmentsTaken.submission_id == submission_id ).first()
	return self_assessment.self_assessment_id

def create_self_assessment_taken(user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_course_id( db, course )
	timestamp = timestamp_type( timestamp )
	submission_id = SubmissionId.get_id( submission )
	self_assessment_id = QuestionSetId.get_id( submission.questionSetId )
	# We likely will not have a grader.
	grader = _get_grader_id( submission )
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
	db.session.flush()
	self_assessment_id = new_object.self_assessment_id

	for assessed_question in submission.questions:
		question_id = assessed_question.questionId

		for idx, part in enumerate( assessed_question.parts ):
			grade = part.assessedValue
			is_correct = grade == 1
			response = _get_response( part.submittedResponse )
			grade_details = SelfAssessmentDetails( user_id=uid,
													session_id=sid,
													timestamp=timestamp,
													self_assessment_id=self_assessment_id,
													question_id=question_id,
													question_part_id=idx,
													is_correct=is_correct,
													grade=grade,
													grader=grader,
													submission=response,
													time_length=time_length )
			db.session.add( grade_details )

def _get_grade( submission ):
	return IGrade( submission, None )

def _get_grader_id( submission ):
	"""
	Returns a grader id for the submission if one exists (otherwise None).
	Currently, we have a one-to-one mapping between submission and grader.  That
	would need to change for things like peer grading.
	"""
	grader = None
	graded_submission = _get_grade( submission )
	# If None, we're pending right?
	if graded_submission is not None:
		grader = get_creator( graded_submission )
		if grader is not None:
			grader = get_or_create_user(grader )
			grader = grader.user_id
	return grader

def _get_assignment_taken_id( db, submission_id ):
	submission = db.session.query(AssignmentsTaken).filter( AssignmentsTaken.submission_id == submission_id ).first()
	return submission.assignment_taken_id

def create_assignment_taken(user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_course_id( db, course )
	timestamp = timestamp_type( timestamp )
	submission_id = SubmissionId.get_id( submission )
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
	db.session.flush()
	assignment_taken_id = new_object.assignment_taken_id

	question_part_dict = dict()

	# Submission Parts
	for set_submission in submission_obj.parts:
		for question_submission in set_submission.questions:
			# Questions don't have ds_intids, just use ntiid.
			question_id = question_submission.questionId
			# We'd like this by part, but will accept by question for now;
			# it's only an estimate anyway.
			time_length = _get_duration( question_submission )

			for idx, part in enumerate( question_submission.parts ):
				# Serialize our response
				response = _get_response( part )
				parts = AssignmentDetails( 	user_id=uid,
											session_id=sid,
											timestamp=timestamp,
											assignment_taken_id=assignment_taken_id,
											question_id=question_id,
											question_part_id=idx,
											submission=response,
											time_length=time_length )
				db.session.add( parts )
				question_part_dict[ (question_id,idx) ] = parts

	db.session.flush()


	# Grade
	graded_submission = _get_grade( submission )
	# If None, we're pending right?
	if graded_submission is not None:
		grade = graded_submission.grade
		grade_num = _get_grade_val( grade )

		grader = _get_grader_id( submission )

		graded = AssignmentGrades( 	user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									assignment_taken_id=assignment_taken_id,
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
					parts = question_part_dict[ (question_id,idx) ]
					grade_details = AssignmentDetailGrades( user_id=uid,
															session_id=sid,
															timestamp=timestamp,
															assignment_details_id=parts.assignment_details_id,
															assignment_taken_id=assignment_taken_id,
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
	submission_id = SubmissionId.get_id( submission )
	assignment_taken_id = _get_assignment_taken_id( db, submission_id )
	grade_entry = _get_grade_entry( db, assignment_taken_id )
	timestamp = timestamp_type( timestamp )

	grade_num = _get_grade_val( graded_val )

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
		sid = SessionId.get_id( nti_session )

		new_object = AssignmentGrades( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										assignment_taken_id=assignment_taken_id,
										grade=graded_val,
										grade_num=grade_num,
										grader=grader_id )

		db.session.add( new_object )

def _get_grade_entry( db, assignment_taken_id ):
	# Currently, one assignment means one grade (and one grader).  If that changes, we'll
	# need to change this (at least)
	grade_entry = db.session.query(AssignmentGrades).filter(
												AssignmentGrades.assignment_taken_id==assignment_taken_id ).first()
	return grade_entry

def _get_grade_id( db, assignment_taken_id ):
	grade_entry = _get_grade_entry( db, assignment_taken_id )
	return grade_entry.grade_id

def create_submission_feedback( user, nti_session, timestamp, submission, feedback ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	timestamp = timestamp_type( timestamp )
	feedback_ds_id = FeedbackId.get_id( feedback )
	feedback_length = sum( len( x ) for x in feedback.body )

	submission_id = SubmissionId.get_id( submission )
	assignment_taken_id = _get_assignment_taken_id( db, submission_id )
	# Do we need to handle any of these being None?
	# That's an error condition, right?
	grade_id = _get_grade_id( db, assignment_taken_id )

	new_object = AssignmentFeedback( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									assignment_taken_id=assignment_taken_id,
									feedback_ds_id=feedback_ds_id,
									feedback_length=feedback_length,
									grade_id=grade_id )
	db.session.add( new_object )

def delete_feedback( timestamp, feedback_ds_id ):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	feedback = db.session.query(AssignmentFeedback).filter(
							AssignmentFeedback.feedback_ds_id == feedback_ds_id ).one()
	feedback.deleted=timestamp
	feedback.feedback_ds_id = None
	db.session.flush()

def _resolve_self_assessment( row ):
	make_transient( row )
	submission = SubmissionId.get_object( row.submission_id )
	course = get_course( row.course_id )
	user = get_user( row.user_id )
	result = None
	if 		submission is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsAssessment( Submission=submission,
										user=user,
										timestamp=row.timestamp,
										RootContextID=course,
										Duration=row.time_length )
	return result

def _resolve_assignment( row, details=None ):
	# We may have multiple assignment records here at one point.
	submission_record = row
	grade_record = submission_record.grade
	make_transient( submission_record )

	grade_num = grade = grader = None
	if grade_record is not None:
		make_transient( grade_record )
		grade_num = grade_record.grade_num
		grade = grade_record.grade
		grader = grade_record.grader

	submission = SubmissionId.get_object( submission_record.submission_id )
	course = get_course( submission_record.course_id )
	user = get_user( submission_record.user_id )
	result = None
	if 		submission is not None \
		and user is not None \
		and course is not None:
		result = AnalyticsAssignment( Submission=submission,
										user=user,
										timestamp=submission_record.timestamp,
										RootContextID=course,
										Duration=submission_record.time_length,
										AssignmentId=submission_record.assignment_id,
										GradeNum=grade_num,
										Grade=grade,
										Grader=grader,
										Details=details )
	return result

def _resolve_assignment_details( row ):
	submission_record, detail_records = row
	details = []

	# Seems like this would be automatic.
	if not isinstance( detail_records, list ):
		detail_records = (detail_records,)

	for detail_record in detail_records:
		make_transient( detail_record )

		grade = grader = is_correct = None
		grade_record = detail_record.grade
		if grade_record:
			grade = grade_record.grade
			grader = grade_record.grader
			is_correct = grade_record.is_correct

		answer = _load_response( detail_record.submission )

		result = AnalyticsAssignmentDetail( QuestionId=detail_record.question_id,
											QuestionPartId=detail_record.question_part_id,
											Answer=answer,
											Duration=detail_record.time_length,
											Grade=grade,
											Grader=grader,
											IsCorrect=is_correct )
		details.append( result )
	return _resolve_assignment( submission_record, details=details )

def get_self_assessments_for_user(user, course):
	db = get_analytics_db()
	user = get_or_create_user( user )
	uid = user.user_id
	course_id = get_course_id( db, course )
	results = db.session.query(SelfAssessmentsTaken).filter( 	SelfAssessmentsTaken.user_id == uid,
																SelfAssessmentsTaken.course_id == course_id ).all()

	return resolve_objects( _resolve_self_assessment, results )

def get_assignments_for_user(user, course):
	# We may not have a grade here.
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	course_id = get_course_id( db, course )
	results = db.session.query( AssignmentsTaken ) \
					.filter( AssignmentsTaken.user_id == uid,
							AssignmentsTaken.course_id == course_id ).all()

	return resolve_objects( _resolve_assignment, results )

def get_self_assessments_for_course(course):
	db = get_analytics_db()
	course_id = get_course_id( db, course )
	results = db.session.query(SelfAssessmentsTaken).filter(
							SelfAssessmentsTaken.course_id == course_id ).all()

	return resolve_objects( _resolve_self_assessment, results )

def get_assignments_for_course(course):
	db = get_analytics_db()
	course_id = get_course_id( db, course )
	results = db.session.query(AssignmentsTaken) \
						.filter( AssignmentsTaken.course_id == course_id ).all()

	return resolve_objects( _resolve_assignment, results )

# AssignmentReport
def get_assignment_grades_for_course(course, assignment_id):
	db = get_analytics_db()
	course_id = get_course_id( db, course )
	results = db.session.query(AssignmentsTaken) \
						.filter( AssignmentsTaken.course_id == course_id,
								 AssignmentsTaken.assignment_id == assignment_id ).all()

	return resolve_objects( _resolve_assignment, results )

def get_assignment_details_for_course(course, assignment_id):
	db = get_analytics_db()
	course_id = get_course_id( db, course )
	results = db.session.query( AssignmentsTaken, AssignmentDetails ) \
						.join( AssignmentDetails ) \
						.filter( AssignmentsTaken.course_id == course_id,
								AssignmentsTaken.assignment_id == assignment_id ).all()

	return resolve_objects( _resolve_assignment_details, results )

