#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from zc.intid.interfaces import IAfterIdAddedEvent
from zc.intid.interfaces import IBeforeIdRemovedEvent

from zope import component

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.analytics import ASSESSMENTS_ANALYTICS

from nti.analytics import get_factory

from nti.analytics.common import get_entity
from nti.analytics.common import get_course
from nti.analytics.common import get_creator
from nti.analytics.common import process_event
from nti.analytics.common import get_object_root
from nti.analytics.common import get_created_timestamp

from nti.analytics.database import assessments as db_assessments

from nti.analytics.identifier import get_ds_id

from nti.analytics.interfaces import IObjectProcessor

from nti.analytics.resolvers import get_root_context
from nti.analytics.resolvers import get_course_for_ntiid

from nti.analytics.sessions import get_nti_session_id

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItem
from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItemFeedback

from nti.app.products.gradebook.interfaces import IGrade

from nti.assessment.interfaces import IQAssessedQuestion
from nti.assessment.interfaces import IQAssessedQuestionSet

from nti.ntiids.ntiids import find_object_with_ntiid

logger = __import__('logging').getLogger(__name__)

component.moduleProvides(IObjectProcessor)

get_self_assessments_for_course = db_assessments.get_self_assessments_for_course
get_self_assessments_for_user = db_assessments.get_self_assessments_for_user
get_assignments_for_user = db_assessments.get_assignments_for_user
get_assignment_for_user = db_assessments.get_assignment_for_user
get_self_assessments_for_user_and_id = db_assessments.get_self_assessments_for_user_and_id
get_self_assessment_views = db_assessments.get_self_assessment_views
get_assignment_views = db_assessments.get_assignment_views


def _get_job_queue():
	factory = get_factory()
	return factory.get_queue(ASSESSMENTS_ANALYTICS)


def _get_course( history_item ):
	course = None
	try:
		course = get_course( history_item )
	except TypeError:
		# Some assignments do not have courses in their lineage (bug?)
		# Brute force it
		submission = getattr( history_item, 'Submission', None )
		assignment_id = getattr( submission, 'assignmentId', None )
		logger.warn( 'No course in assessment lineage (%s) (parent=%s) (assignment_id=%s)',
					history_item,
					history_item.__parent__,
					assignment_id )

		if assignment_id is not None:
			course = get_course_for_ntiid( assignment_id )
	if course is None:
		raise TypeError( 'No course found for history item (%s)', history_item )

	return course


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


@component.adapter(IQAssessedQuestionSet, IAfterIdAddedEvent)
def _questionset_assessed( question_set, unused_event ):
	# We'll have creator for self-assessments, but not for assignments,
	# which we throw away anyway.
	nti_session = get_nti_session_id()
	_process_question_set( question_set, nti_session=nti_session )


@component.adapter(IQAssessedQuestion, IAfterIdAddedEvent)
def _question_grade( question, event ):
	# These are question level grade events (also modified). These do
	# not currently occur in the wild, but they may in the future.
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
		course = _get_course( submission )
		obj = db_assessments.create_assignment_taken( user, nti_session, timestamp, course, submission )
		logger.debug("Assignment submitted (user=%s) (assignment=%s)", user, submission.assignmentId )

		if obj:
			for feedback in submission.Feedback.values():
				_do_add_feedback( nti_session, feedback, submission )


@component.adapter(IUsersCourseAssignmentHistoryItem, IAfterIdAddedEvent)
def _assignment_history_item_added( item, unused_event ):
	nti_session = get_nti_session_id()
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
	# Perhaps a grade is being assigned without a submission. That should be a rare case
	# and is not something useful to persist.
	# This is quite common. This will be a MetaGrade stored on the grade container. Not
	# sure this is useful to store outside of a submission.
	if submission is None or not grade.creator:
		return
	user = get_creator( grade )
	nti_session = get_nti_session_id()
	timestamp = datetime.utcnow()
	graded_val = grade.value
	process_event( _get_job_queue,
					_set_grade,
					submission,
					username=getattr( user, 'username', None),
					graded_val=graded_val,
					nti_session=nti_session,
					timestamp=timestamp )


@component.adapter(IGrade, IObjectModifiedEvent)
def _grade_modified(grade, unused_event):
	submission = IUsersCourseAssignmentHistoryItem( grade )
	_grade_submission( grade, submission )


@component.adapter(IGrade, IAfterIdAddedEvent)
def _grade_added(grade, unused_event):
	submission = IUsersCourseAssignmentHistoryItem( grade, None )
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


def _update_feedback( oid, nti_session=None ):
	feedback = find_object_with_ntiid(oid)
	if feedback is not None:
		submission = get_object_root( feedback, IUsersCourseAssignmentHistoryItem )
		user = get_creator( feedback )
		timestamp = get_created_timestamp(feedback)
		db_assessments.update_feedback(user, nti_session,
										timestamp, submission, feedback )
		logger.debug( "Assignment feedback updated (user=%s) (%s)", user, feedback )


def _remove_feedback( feedback_id, timestamp=None ):
	db_assessments.delete_feedback( timestamp, feedback_id )
	logger.debug("Assignment feedback removed (%s)", feedback_id )


@component.adapter(IUsersCourseAssignmentHistoryItemFeedback, IAfterIdAddedEvent)
def _feedback_added(feedback, unused_event):
	nti_session = get_nti_session_id()
	process_event( _get_job_queue, _add_feedback, feedback, nti_session=nti_session )


@component.adapter(IUsersCourseAssignmentHistoryItemFeedback, IObjectModifiedEvent)
def _feedback_updated(feedback, unused_event):
	nti_session = get_nti_session_id()
	process_event(_get_job_queue, _update_feedback, feedback, nti_session=nti_session)


@component.adapter(IUsersCourseAssignmentHistoryItemFeedback, IBeforeIdRemovedEvent)
def _feedback_removed(feedback, unused_event):
	timestamp = datetime.utcnow()
	feedback_id = get_ds_id( feedback )
	process_event(_get_job_queue, _remove_feedback, feedback_id=feedback_id, timestamp=timestamp)


def init( obj ):
	result = True
	if IQAssessedQuestionSet.providedBy(obj):
		_process_question_set( obj )
	elif IUsersCourseAssignmentHistoryItem.providedBy(obj):
		process_event( _get_job_queue, _assignment_taken, obj )
	else:
		result = False
	return result
