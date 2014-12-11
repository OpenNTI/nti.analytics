#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from zope import component
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem
from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItemFeedback

from nti.app.products.gradebook.interfaces import IGrade

from nti.assessment.interfaces import IQAssessedQuestion
from nti.assessment.interfaces import IQAssessedQuestionSet

from nti.intid.interfaces import IIntIdAddedEvent
from nti.intid.interfaces import IIntIdRemovedEvent

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.analytics.sessions import get_nti_session_id

from nti.analytics.resolvers import get_root_context

from . import get_factory
from . import ASSESSMENTS_ANALYTICS

from .common import get_entity
from .common import get_course
from .common import get_creator
from .common import process_event
from .common import get_object_root
from .common import get_created_timestamp

from .database import assessments as db_assessments

from nti.analytics.identifier import FeedbackId

from .interfaces import IObjectProcessor

component.moduleProvides(IObjectProcessor)

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue(ASSESSMENTS_ANALYTICS)

def get_self_assessments_for_user( *args, **kwargs ):
	"Retrieves all self-assessments for the given user and course."
	return db_assessments.get_self_assessments_for_user( *args, **kwargs  )

def get_assignments_for_user( *args, **kwargs  ):
	"Retrieves all assignments for the given user and course."
	return db_assessments.get_assignments_for_user( *args, **kwargs )

def get_assignment_for_user( *args, **kwargs  ):
	"Pulls all assignment records for the given user matching the passed in assignment id."
	return db_assessments.get_assignment_for_user( *args, **kwargs )

def get_self_assessments_for_user_and_id( *args, **kwargs  ):
	"Pulls all assessment records for the given user matching the passed in assessment id."
	return db_assessments.get_self_assessments_for_user_and_id( *args, **kwargs )

def _self_assessment_taken( oid, nti_session=None ):
	submission = find_object_with_ntiid( oid )
	if submission is not None:
		user = get_creator( submission )
		timestamp = get_created_timestamp( submission )

		__traceback_info__ = submission.containerId
		course = get_root_context( submission )
		db_assessments.create_self_assessment_taken(user, nti_session,
													timestamp, course, submission)
		logger.debug("Self-assessment submitted (user=%s) (assignment=%s)",
					 user, submission.questionSetId )

def _process_question_set( question_set, nti_session=None ):
	# We only want self-assessments here.
	assignment = get_object_root(question_set,
								 IUsersCourseAssignmentHistoryItem )
	if assignment is None:
		# Ok, we should be a self-assessment.
		process_event( _get_job_queue, _self_assessment_taken,
					  question_set, nti_session=nti_session )
	else:
		# Like individually assessed questions, there are not current cases
		# in the wild where QuestionSets are assessed for an assignment.  Once
		# there are, we should handle those cases here.
		pass

@component.adapter(IQAssessedQuestionSet, IIntIdAddedEvent)
def _questionset_assessed( question_set, event ):
	# We'll have creator for self-assessments, but not for assignments,
	# which we throw away anyway.
	user = get_creator( question_set )
	nti_session = get_nti_session_id( user )
	_process_question_set( question_set, nti_session=nti_session )

@component.adapter(IQAssessedQuestion, IIntIdAddedEvent)
def _question_grade( question, event ):
	# These are question level grade events (also modified). These do
	# not currently occur in the wild, but they may in the future.
	# TODO implement
	# We're not subscribed to any event listeners either.
	pass

@component.adapter(IQAssessedQuestion, IObjectModifiedEvent)
def _question_grade_modified( question, event ):
	pass

# Assignments
def _assignment_taken( oid, nti_session=None ):
	submission = find_object_with_ntiid(oid)
	if submission is not None:
		user = get_creator( submission )
		timestamp = get_created_timestamp( submission )
		course = get_course( submission )
		db_assessments.create_assignment_taken( user, nti_session, timestamp, course, submission )
		logger.debug("Assignment submitted (user=%s) (assignment=%s)", user, submission.assignmentId )

		for feedback in submission.Feedback.values():
			_do_add_feedback( nti_session, feedback, submission )

@component.adapter(IUsersCourseAssignmentHistoryItem, IIntIdAddedEvent)
def _assignment_history_item_added( item, event ):
	user = get_creator( item )
	nti_session = get_nti_session_id( user )
	process_event( _get_job_queue, _assignment_taken, item, nti_session=nti_session )

def _set_grade( oid, username, graded_val, nti_session=None, timestamp=None ):
	submission = find_object_with_ntiid(oid)
	if submission is not None:
		grader = get_entity( username )
		user = get_creator( submission )
		db_assessments.grade_submission(user, nti_session, timestamp,
										grader, graded_val, submission )
		assignment_id = getattr( submission, 'assignmentId', None )

		logger.debug("Setting grade for assignment "
					 "(user=%s) (grade=%s) (grader=%s) (assignment=%s)",
					 user,
					 graded_val,
					 grader,
					 assignment_id )

def _grade_submission( grade, submission ):
	user = get_creator( grade )
	nti_session = get_nti_session_id( user )
	timestamp = datetime.utcnow()
	graded_val = grade.grade
	process_event( _get_job_queue,
					_set_grade,
					submission,
					username=user.username,
					graded_val=graded_val,
					nti_session=nti_session,
					timestamp=timestamp )

@component.adapter(IGrade, IObjectModifiedEvent)
def _grade_modified(grade, event):
	submission = IUsersCourseAssignmentHistoryItem( grade )
	_grade_submission( grade, submission )

@component.adapter(IGrade, IIntIdAddedEvent)
def _grade_added(grade, event):
	submission = IUsersCourseAssignmentHistoryItem( grade, None )
	# Perhaps a grade is being assigned without a submission.  That should be a rare case
	# and is not something useful to persist.
	# TODO Oof, a placeholder submission is created. See if we can tell when that occurs.
	# (it also appears in the Grade modified path).
	if submission is None:
		return
	_grade_submission( grade, submission )

def _do_add_feedback( nti_session, feedback, submission ):
	user = get_creator( feedback )
	timestamp = get_created_timestamp(feedback)
	db_assessments.create_submission_feedback(user, nti_session,
											  timestamp, submission, feedback )
	logger.debug( "Assignment feedback added (user=%s) (%s)", user, feedback )

# Feedback
def _add_feedback( oid, nti_session=None ):
	feedback = find_object_with_ntiid(oid)
	if feedback is not None:
		submission = get_object_root( feedback, IUsersCourseAssignmentHistoryItem )
		_do_add_feedback( nti_session, feedback, submission )

def _remove_feedback( feedback_id, timestamp=None ):
	db_assessments.delete_feedback( timestamp, feedback_id )
	logger.debug("Assignment feedback removed (%s)", feedback_id )

@component.adapter(IUsersCourseAssignmentHistoryItemFeedback, IIntIdAddedEvent)
def _feedback_added(feedback, event):
	user = get_creator( feedback )
	nti_session = get_nti_session_id( user )
	process_event( _get_job_queue, _add_feedback, feedback, nti_session=nti_session )

@component.adapter(IUsersCourseAssignmentHistoryItemFeedback, IIntIdRemovedEvent)
def _feedback_removed(feedback, event):
	timestamp = datetime.utcnow()
	feedback_id = FeedbackId.get_id( feedback )
	process_event( _get_job_queue, _remove_feedback, feedback_id=feedback_id, timestamp=timestamp )

def init( obj ):
	result = True
	if IQAssessedQuestionSet.providedBy(obj):
		_process_question_set( obj )
	elif IUsersCourseAssignmentHistoryItem.providedBy(obj):
		process_event( _get_job_queue, _assignment_taken, obj )
	else:
		result = False
	return result
