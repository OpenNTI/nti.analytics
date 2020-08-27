#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import json

from six import string_types
from six import integer_types

from zope import interface

from nti.analytics_database.assessments import AssignmentViews
from nti.analytics_database.assessments import AssignmentGrades
from nti.analytics_database.assessments import AssignmentsTaken
from nti.analytics_database.assessments import AssignmentDetails
from nti.analytics_database.assessments import AssignmentFeedback
from nti.analytics_database.assessments import SelfAssessmentViews
from nti.analytics_database.assessments import SelfAssessmentsTaken
from nti.analytics_database.assessments import SelfAssessmentDetails
from nti.analytics_database.assessments import AssignmentDetailGrades
from nti.analytics_database.assessments import FeedbackUserFileUploadMimeTypes

from nti.analytics.common import get_creator
from nti.analytics.common import timestamp_type
from nti.analytics.common import get_created_timestamp
from nti.analytics.common import get_course as get_course_from_object

from nti.analytics.identifier import get_ds_id
from nti.analytics.identifier import get_ntiid_id

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database._utils import get_context_path
from nti.analytics.database._utils import get_body_text_length

from nti.analytics.database.query_utils import get_record_count_by_user

from nti.analytics.database.mime_types import build_mime_type_records

from nti.analytics.database.resources import get_resource_record

from nti.analytics.database.root_context import get_root_context_record

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.users import get_or_create_user

from nti.app.products.gradebook.interfaces import IGrade

from nti.assessment.common import grader_for_response

from nti.assessment.interfaces import IQUploadedFile
from nti.assessment.interfaces import IQAssessedQuestionSet
from nti.assessment.interfaces import IQModeledContentResponse
from nti.assessment.interfaces import IQAssignmentDateContext

from nti.assessment.randomized.interfaces import IQRandomizedPart
from nti.assessment.randomized.interfaces import IRandomizedPartsContainer

from nti.ntiids.ntiids import find_object_with_ntiid

logger = __import__('logging').getLogger(__name__)


def _get_duration( submission ):
	"""
	For a submission, retrieves how long it took to submit the object, in
	integer seconds. '-1' is returned if unknown.
	"""
	time_length = getattr( submission, 'CreatorRecordedEffortDuration', -1 )
	time_length = time_length or -1
	return int( time_length )


def _get_response(user, question_part, response, contextually_randomized=False):
	"""
	For a submission part, return the user-provided response.
	"""
	# Part should only be None for unit tests.
	if 		question_part is not None \
		and (	contextually_randomized
			 or IQRandomizedPart.providedBy(question_part)) \
		and response is not None:
		# XXX Need a migration for these in the db.

		# First de-randomize our question part, if necessary.
		grader = grader_for_response( question_part, response )
		if grader is not None:
			response = grader.unshuffle(response,
										user=user,
										context=question_part)

	if IQUploadedFile.providedBy( response ):
		response = '<FILE_UPLOADED>'
	elif IQModeledContentResponse.providedBy( response ):
		response = ''.join( response.value )

	result = ''
	try:
		# Hmm, json will convert the keys to string as we dump them.  We
		# could try to handle that, or we could serialize differently.
		# I think, most importantly, we need to compare responses between users
		# (which this will handle) and to know if the answer was correct.
		# We may be fine as-is with json.
		result = json.dumps(response)
	except TypeError:
		logger.info('Submission response is not serializable (type=%s)',
					type(response))

	return result


def _load_response( value ):
	"""
	For a database response value, transform it into a useable state.
	"""
	response = json.loads( value )
	if isinstance( response, dict ):
		# Convert to int keys, if possible.
		# We currently do not handle mixed types of keys.
		try:
			response = {int( x ): y for x,y in response.items()}
		except ValueError:
			pass
	return response


def _get_grade_val( grade_value ):
	"""
	Convert the webapp's "number - letter" scheme to a number, or None.
	"""
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
	self_assessment = db.session.query(SelfAssessmentsTaken).filter(
									SelfAssessmentsTaken.submission_id == submission_id ).first()
	return self_assessment and self_assessment.self_assessment_id

_self_assessment_exists = _get_self_assessment_id


def create_self_assessment_taken(user, nti_session, timestamp, course, submission):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	sid = nti_session
	root_context_record = get_root_context_record(db, course, create=True)
	timestamp = timestamp_type( timestamp )
	submission_id = get_ds_id( submission )

	if _self_assessment_exists( db, submission_id ):
		logger.warn( "Self-assessment already exists (ds_id=%s) (user=%s) ",
					submission_id, user )
		return False

	self_assessment_id = get_ntiid_id( submission.questionSetId )
	# We likely will not have a grader.
	grader = _get_grader_record(submission)
	# TODO: As a QAssessedQuestionSet. we will not have a duration.
	# I don't believe the submission was saved; so we cannot get it back.
	# We'd have to transfer it during adaptation perhaps.
	time_length = _get_duration( submission )

	new_object = SelfAssessmentsTaken(session_id=sid,
									  timestamp=timestamp,
									  assignment_id=self_assessment_id,
									  submission_id=submission_id,
									  time_length=time_length)
	new_object._root_context_record = root_context_record
	new_object._user_record = user_record
	db.session.add(new_object)
	self_assessment_id = new_object.self_assessment_id
	qset = find_object_with_ntiid( submission.questionSetId )

	for assessed_question in submission.questions:
		question_id = assessed_question.questionId
		question = find_object_with_ntiid( question_id )

		for idx, part in enumerate( assessed_question.parts ):
			grade = part.assessedValue
			is_correct = grade == 1
			question_part = question.parts[idx] if question is not None else None

			# Mark randomized if question set is a randomized parts container.
			contextually_randomized = IRandomizedPartsContainer.providedBy(qset)
			response = _get_response(user, question_part, part.submittedResponse,
									 contextually_randomized=contextually_randomized)

			grade_details = SelfAssessmentDetails(session_id=sid,
												  timestamp=timestamp,
												  self_assessment_id=self_assessment_id,
												  question_id=question_id,
												  question_part_id=idx,
												  is_correct=is_correct,
												  grade=grade,
												  submission=response,
												  time_length=time_length)
			grade_details._user_record = user_record
			grade_details._grader_record = grader
			new_object.details.append(grade_details)
	return new_object


def _get_grade(submission):
	return IGrade(submission, None)


def _get_grader_record( submission ):
	"""
	Returns a grader id for the submission if one exists (otherwise None).
	Currently, we have a one-to-one mapping between submission and grader.  That
	would need to change for things like peer grading.
	"""
	grader = None
	grade_obj = _get_grade( submission )
	# If None, we're pending right?
	if grade_obj is not None:
		grader = get_creator(grade_obj)
		if grader is not None:
			grader = get_or_create_user(grader)
	return grader


def _is_late( course, submission ):
	assignment = submission.Assignment
	date_context = IQAssignmentDateContext( course )
	due_date = date_context.of( assignment ).available_for_submission_ending
	submitted_late = submission.created > due_date if due_date else False
	return submitted_late


def _get_assignment_taken_id( db, submission_id ):
	submission = db.session.query(AssignmentsTaken).filter( AssignmentsTaken.submission_id == submission_id ).first()
	return submission and submission.assignment_taken_id

_assignment_taken_exists = _get_assignment_taken_id


def create_assignment_taken( user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	sid = nti_session
	root_context_record = get_root_context_record(db, course, create=True)
	timestamp = timestamp_type( timestamp )
	submission_id = get_ds_id( submission )

	if _assignment_taken_exists( db, submission_id ):
		logger.warn( 'Assignment taken already exists (ds_id=%s) (user=%s)',
					submission_id, user )
		return False

	assignment_id = submission.assignmentId
	submission_obj = submission.Submission
	time_length = _get_duration( submission_obj )
	is_late = _is_late( course, submission )

	new_object = AssignmentsTaken(session_id=sid,
								  timestamp=timestamp,
								  assignment_id=assignment_id,
								  submission_id=submission_id,
								  is_late=is_late,
								  time_length=time_length)
	new_object._root_context_record = root_context_record
	new_object._user_record = user_record
	db.session.add(new_object)
	assignment_taken_id = new_object.assignment_taken_id

	question_part_dict = dict()

	# Submission Parts
	for set_submission in submission_obj.parts:
		for question_submission in set_submission.questions:
			qset = find_object_with_ntiid( set_submission.questionSetId )
			# Questions don't have ds_intids, just use ntiid.
			question_id = question_submission.questionId
			question = find_object_with_ntiid( question_id )
			# We'd like this by part, but will accept by question for now;
			# it's only an estimate anyway.
			time_length = _get_duration( question_submission )

			for idx, response in enumerate( question_submission.parts ):
				# Serialize our response
				question_part = question.parts[idx] if question is not None else None
				logger.info( 'Getting response for (aid=%s) (user=%s) (q=%s) (idx=%s) (submission=%s)',
							 assignment_id, user, question_id, idx, submission_id)

				contextually_randomized = IRandomizedPartsContainer.providedBy(qset)
				response = _get_response(user, question_part, response,
										 contextually_randomized=contextually_randomized)
				parts = AssignmentDetails( 	session_id=sid,
											timestamp=timestamp,
											assignment_taken_id=assignment_taken_id,
											question_id=question_id,
											question_part_id=idx,
											submission=response,
											time_length=time_length )
				parts._user_record = user_record
				new_object.details.append( parts )
				question_part_dict[ (question_id,idx) ] = parts

	# Grade
	graded_submission = _get_grade( submission )

	# If None, we're pending right?
	if graded_submission is not None:
		grade = graded_submission.grade
		grade_num = _get_grade_val( grade )

		grader = _get_grader_record( submission )

		graded = AssignmentGrades( 	session_id=sid,
									timestamp=timestamp,
									assignment_taken_id=assignment_taken_id,
									grade=grade,
									grade_num=grade_num)
		graded._user_record = user_record
		graded._grader_record = grader
		new_object.grade = graded

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
					grade_details = AssignmentDetailGrades( session_id=sid,
															timestamp=timestamp,
															question_id=question_id,
															question_part_id=idx,
															is_correct=is_correct,
															grade=str(grade))
					grade_details._user_record = user_record
					grade_details._grader_record = grader
					parts.grade = grade_details
					new_object.grade_details.append(grade_details)
	return new_object


def grade_submission( user, nti_session, timestamp, grader, graded_val, submission ):
	# The server creates an assignment placeholder if a grade
	# is received without a submission, which should jive with
	# what we are expecting here.

	db = get_analytics_db()
	grader = get_or_create_user(grader)
	submission_id = get_ds_id( submission )
	assignment_taken = db.session.query(AssignmentsTaken).filter(AssignmentsTaken.submission_id == submission_id).first()

	if assignment_taken is None:
		# Somehow, in prod, we got a grade before a placeholder submission event.
		course = get_course_from_object( submission )
		create_assignment_taken( user, nti_session, timestamp, course, submission )
		logger.info( 'Creating assignment taken (user=%s) (submission=%s)', user, submission )
		# Creating an assignment also takes care of the grade
		return

	grade_entry = _get_grade_entry( db, assignment_taken.assignment_taken_id )
	timestamp = timestamp_type( timestamp )

	grade_num = _get_grade_val( graded_val )

	if grade_entry:
		# Update
		# If we wanted, we could just append every 'set_grade' action.
		grade_entry.grade = graded_val
		grade_entry.grade_num = grade_num
		grade_entry.timestamp = timestamp
		grade_entry._grader_record = grader
	else:
		# New grade
		user = get_or_create_user(user)
		sid = nti_session
		new_object = AssignmentGrades(session_id=sid,
									  timestamp=timestamp,
									  grade=graded_val,
									  grade_num=grade_num)
		new_object._user_recod = user
		new_object._grader_record = grader
		assignment_taken.grade = new_object


def _get_grade_entry( db, assignment_taken_id ):
	# Currently, one assignment means one grade (and one grader).  If that changes, we'll
	# need to change this (at least)
	grade_entry = db.session.query(AssignmentGrades).filter(
								   AssignmentGrades.assignment_taken_id==assignment_taken_id ).first()
	return grade_entry


def _get_grade_id( db, assignment_taken_id ):
	grade_entry = _get_grade_entry( db, assignment_taken_id )
	return grade_entry.grade_id


def _get_feedback( db, feedback_ds_id ):
	feedback = db.session.query( AssignmentFeedback ).filter(
							 AssignmentFeedback.feedback_ds_id == feedback_ds_id ).first()
	return feedback


def _feedback_exists( db, feedback_ds_id ):
	return _get_feedback( db, feedback_ds_id ) is not None


def _set_mime_records( db, feedback_record, feedback ):
	"""
	Set the mime type records for our feedback, removing any
	previous records present.
	"""
	# Delete the old records.
	for mime_record in feedback_record._file_mime_types:
		db.session.delete( mime_record )
	feedback_record._file_mime_types = []

	file_mime_types = build_mime_type_records( db, feedback, FeedbackUserFileUploadMimeTypes )
	feedback_record._file_mime_types.extend( file_mime_types )


def _set_feedback_attributes( db, feedback_record, feedback ):
	"""
	Set the feedback attributes for this feedback record.
	"""
	feedback_record.feedback_length = get_body_text_length( feedback )
	_set_mime_records( db, feedback_record, feedback )


def create_submission_feedback( user, nti_session, timestamp, submission, feedback ):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	sid = nti_session
	timestamp = timestamp_type( timestamp )
	feedback_ds_id = get_ds_id( feedback )

	if _feedback_exists( db, feedback_ds_id ):
		logger.warn( 'Feedback exists (ds_id=%s) (user=%s)', feedback_ds_id, user )
		return

	submission_id = get_ds_id( submission )
	assignment_taken = db.session.query(AssignmentsTaken).filter(AssignmentsTaken.submission_id == submission_id).first()

	if assignment_taken is None:
		assignment_creator = get_creator( submission )
		timestamp = get_created_timestamp( submission )
		course = get_course_from_object( submission )
		assignment_taken = create_assignment_taken( assignment_creator, None, timestamp, course, submission )
		logger.info( 'Assignment created (%s) (%s)', assignment_creator, submission )

	# Do we need to handle any of these being None?
	# That's an error condition, right?
	grade_id = _get_grade_id( db, assignment_taken.assignment_taken_id )

	new_object = AssignmentFeedback(session_id=sid,
									timestamp=timestamp,
									feedback_ds_id=feedback_ds_id,
									grade_id=grade_id )
	new_object._user_record = user_record
	_set_feedback_attributes( db, new_object, feedback )
	assignment_taken.feedback.append(new_object)
	return new_object


def update_feedback( user, nti_session, timestamp, submission, feedback ):
	"""
	Update our feedback record, creating if it does not exist.
	"""
	db = get_analytics_db()
	feedback_ds_id = get_ds_id(feedback)
	feedback_record = _get_feedback(db, feedback_ds_id)
	if feedback_record is None:
		create_submission_feedback( user, nti_session, timestamp, submission, feedback )
	else:
		_set_feedback_attributes( db, feedback_record, feedback )


def delete_feedback( timestamp, feedback_ds_id ):
	db = get_analytics_db()
	timestamp = timestamp_type( timestamp )
	feedback = db.session.query(AssignmentFeedback).filter(
								AssignmentFeedback.feedback_ds_id == feedback_ds_id ).first()
	if not feedback:
		logger.info( 'Feedback never created (%s)', feedback_ds_id )
		return
	feedback.deleted=timestamp
	feedback.feedback_ds_id = None


def _assess_view_exists(db, table, user_id, assessment_id, timestamp,
						assessment_column_name):
	"""
	Check if the given record (defined by timestamp, assessment_id, and table)
	exists already. If so, we return the record.
	"""
	filters = [table.user_id == user_id,
			   table.timestamp == timestamp]
	filters.append(getattr(table, assessment_column_name) == assessment_id)
	return db.session.query(table).filter(*filters).first()


def create_assessment_view(table, user, nti_session, timestamp, course,
						   context_path, resource, time_length, assessment_id,
						   assessment_column_name='assignment_id'):
	"""
	Create a basic assessment view event, if necessary. Also if necessary, may
	 update existing events with appropriate data.
	"""
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	sid = nti_session
	resource_record = None
	if resource is not None:
		rid = get_ntiid_id(resource)
		resource_record = get_resource_record(db, rid, create=True)

	root_context_record = get_root_context_record(db, course, create=True)
	timestamp = timestamp_type( timestamp )

	existing_record = _assess_view_exists(db, table, user_record.user_id, assessment_id,
										  timestamp, assessment_column_name)
	if existing_record is not None:
		if should_update_event(existing_record, time_length):
			existing_record.time_length = time_length
			return
		else:
			logger.warn("""%s view already exists (user=%s) (assessment_id=%s)
						(timestamp=%s) (time_length=%s)""",
						table.__tablename__, user, assessment_id, timestamp,
						time_length)
			return
	context_path = get_context_path(context_path)

	new_object = table( session_id=sid,
						timestamp=timestamp,
						context_path=context_path,
						time_length=time_length)
	setattr(new_object, assessment_column_name, assessment_id)
	new_object._resource = resource_record
	new_object._root_context_record = root_context_record
	new_object._user_record = user_record
	db.session.add(new_object)
	return new_object


def create_self_assessment_view(user, nti_session, timestamp, course,
								context_path, resource, time_length,
								assignment_id):
	return create_assessment_view(SelfAssessmentViews, user, nti_session,
								  timestamp, course, context_path, resource,
								  time_length, assignment_id)


def create_assignment_view(user, nti_session, timestamp, course, context_path,
						   resource, time_length, assignment_id):
	return create_assessment_view(AssignmentViews, user, nti_session,
								  timestamp, course, context_path, resource,
								  time_length, assignment_id)


def _resolve_self_assessment( row, user=None, course=None ):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	return row


def _resolve_assignment( row, details=None, user=None, course=None ):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	if details is not None:
		row.Details = details
	return row


def get_self_assessments_for_user(user, course=None, **kwargs ):
	"""
	Retrieves all self-assessments for the given user and course.
	"""
	results = get_filtered_records( user, SelfAssessmentsTaken, course=course, **kwargs )
	return resolve_objects( _resolve_self_assessment, results, user=user, course=course )


def get_self_assessments_for_user_and_id(user, assessment_id):
	"""
	Pulls all assessment records for the given user matching the passed in
	assessment id.
	"""
	filters = (SelfAssessmentsTaken.assignment_id == assessment_id,)
	results = get_self_assessments_for_user(user, filters=filters)
	return results


def get_assignments_for_user(user, course=None, **kwargs):
	"""
	Retrieves all assignments for the given user and course.
	"""
	results = get_filtered_records( user, AssignmentsTaken, course=course, **kwargs )
	return resolve_objects( _resolve_assignment, results, user=user, course=course )


def get_assignment_for_user( user, assignment_id ):
	"""
	Pulls all assignment records for the given user matching the passed in assignment id.
	"""
	filters = (AssignmentsTaken.assignment_id == assignment_id,)
	results = get_assignments_for_user(user, filters=filters)
	return results


def get_self_assessments_for_course(course):
	return get_self_assessments_for_user(None, course=course)


def get_assignments_for_course(course):
	return get_assignments_for_user(None, course=course)


# AssignmentReport
def get_assignment_grades_for_course(course, assignment_id):
	filters = (AssignmentsTaken.assignment_id == assignment_id,)
	results = get_assignments_for_user(None, course=course, filters=filters)
	return results

get_assignment_details_for_course = get_assignment_grades_for_course


def _resolve_view( row, course, user ):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	return row


def _resolve_self_assessment_view( row, user=None, course=None ):
	return _resolve_view( row, course, user )


def _resolve_assignment_view( row, user=None, course=None ):
	return _resolve_view( row, course, user )


def _resolve_assignment_taken_view( row, user=None, course=None ):
	return _resolve_view( row, course, user )


def get_self_assessment_views( user, course=None, **kwargs ):
	"""
	Fetch any self assessment views for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_filtered_records(user, SelfAssessmentViews,
								   course=course, **kwargs)
	return resolve_objects(_resolve_self_assessment_view, results,
						   user=user, course=course)


def get_assignment_views( user, course=None, **kwargs ):
	"""
	Fetch any assignment views for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_filtered_records( user, AssignmentViews,
								 	course=course, **kwargs )
	return resolve_objects(_resolve_assignment_view, results,
						   user=user, course=course )


def get_assignment_taken_views( user=None, course=None, **kwargs ):
	"""
	Fetch any assignment takens for a user created *after* the optionally given
	timestamp.  Optionally, can filter by course.
	"""
	results = get_filtered_records( user, AssignmentsTaken,
									course=course, **kwargs )
	return resolve_objects(_resolve_assignment_taken_view, results,
						   user=user, course=course )


def get_assignments_taken_by_user(root_context=None, **kwargs):

	return get_record_count_by_user(AssignmentsTaken, root_context=root_context, **kwargs)
