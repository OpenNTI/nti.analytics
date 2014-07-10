#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from nti.ntiids import ntiids

from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.app.assessment import interfaces as app_assessment_interfaces
from nti.app.products.courseware import interfaces as course_interfaces
from nti.app.products.gradebook import interfaces as grade_interfaces
from nti.assessment import interfaces as assessment_interfaces

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.intid import interfaces as intid_interfaces

from nti.assessment.interfaces import IQAssignment
from nti.app.products.gradebook.interfaces import IGrade

from datetime import datetime

from .common import to_external_ntiid_oid
from .common import get_creator
from .common import get_nti_session_id
from .common import get_deleted_time
from .common import get_comment_root
from .common import get_course
from .common import get_course_by_ntiid
from .common import process_event
from .common import get_created_timestamp
from .common import get_entity
from .common import IDLookup

from . import utils
from . import interfaces as analytic_interfaces

def _self_assessment_taken( db, oid, nti_session=None, time_length=None ):
	submission = ntiids.find_object_with_ntiid( oid )
	if submission is not None:
		user = get_creator( submission )
		timestamp = get_created_timestamp( submission )
		course = get_course_by_ntiid( submission.containerId )
		db.create_self_assessment_taken( user, nti_session, timestamp, course, time_length, submission )
		logger.debug("Self-assessment submitted (user=%s) (assignment=%s)", user, submission.questionSetId )

def _process_question_set( question_set, nti_session=None ):
	# We only want self-assessments here.
 	# FIXME rename this
 	assignment = get_comment_root( question_set, app_assessment_interfaces.IUsersCourseAssignmentHistoryItem )
 	if assignment is None:
  		# Ok, we should be a self-assessment.
	  	process_event( _self_assessment_taken, question_set, nti_session=nti_session )
	else:
		# TODO Like individually assessed questions, there are not current cases
		# in the wild where QuestionSets are assessed for an assignment.  Once
		# there are, we should handle those cases here.
		pass
	

@component.adapter(assessment_interfaces.IQAssessedQuestionSet,
				   intid_interfaces.IIntIdAddedEvent)
def _questionset_assessed( question_set, event ):
	user = get_creator( question_set )
	nti_session = get_nti_session_id( user )
	_process_question_set( question_set, nti_session=nti_session )

@component.adapter(assessment_interfaces.IQAssessedQuestion,
				   intid_interfaces.IIntIdAddedEvent)
def _question_grade( question, event ):
	# These are question level grade events (also modified). These do
	# not currently occur in the wild, but they may in the future.
	# TODO implement
	# We're not subscribed to any event listeners either.
	pass

@component.adapter(assessment_interfaces.IQAssessedQuestion,
				   lce_interfaces.IObjectModifiedEvent)
def _question_grade_modified( question, event ):
	pass

# Assignments
# TODO time-length
def _assignment_taken( db, oid, nti_session=None, time_length=None ):
	submission = ntiids.find_object_with_ntiid(oid)
	if submission is not None:
		user = get_creator( submission )
		timestamp = get_created_timestamp( submission )
		course = get_course( submission )
		db.create_assignment_taken( user, nti_session, timestamp, course, time_length, submission )
		logger.debug("Assignment submitted (user=%s) (assignment=%s)", user, submission.assignmentId )
		
		for feedback in submission.Feedback.values():
			_do_add_feedback( db, nti_session, feedback, submission )

@component.adapter(app_assessment_interfaces.IUsersCourseAssignmentHistoryItem,
				   intid_interfaces.IIntIdAddedEvent)
def _assignment_history_item_added( item, event ):
	user = get_creator( item )
	nti_session = get_nti_session_id( user )
	process_event( _assignment_taken, item, nti_session=nti_session )

def _set_grade( db, oid, username, graded_val, nti_session=None, timestamp=None ):
	submission = ntiids.find_object_with_ntiid(oid)
	if submission is not None:
		grader = get_entity( username )
		user = get_creator( submission )
		db.grade_submission( user, nti_session, timestamp, grader, graded_val, submission )
		assignment_id = getattr( submission, 'assignmentId', None )
		logger.debug( 	"Setting grade for assignment (user=%s) (grade=%s) (grader=%s) (assignment=%s)", 
						user, 
						graded_val,
						grader,
						assignment_id )

def _grade_submission( grade, submission ):
	user = get_creator( grade )
	nti_session = get_nti_session_id( user )
	timestamp = datetime.utcnow()
	graded_val = grade.grade
	process_event( 	_set_grade, 
					submission, 
					username=user.username, 
					graded_val=graded_val, 
					nti_session=nti_session, 
					timestamp=timestamp )

@component.adapter(grade_interfaces.IGrade,
				   lce_interfaces.IObjectModifiedEvent)
def _grade_modified(grade, event):
	submission = app_assessment_interfaces.IUsersCourseAssignmentHistoryItem( grade )
	_grade_submission( grade, submission )

@component.adapter(grade_interfaces.IGrade,
				   intid_interfaces.IIntIdAddedEvent)
def _grade_added(grade, event):
	submission = app_assessment_interfaces.IUsersCourseAssignmentHistoryItem( grade, None )
	# Perhaps a grade is being assigned without a submission.  That should be a rare case
	# and is not something useful to persist.
	if submission is None:
		return
	_grade_submission( grade, submission )

def _do_add_feedback( db, nti_session, feedback, submission ):
	user = get_creator( feedback )
	timestamp = get_created_timestamp( feedback )
		
	db.create_submission_feedback( user, nti_session, timestamp, submission, feedback )
	logger.debug( "Assignment feedback added (user=%s) (%s)", user, feedback )

# Feedback
def _add_feedback( db, oid, nti_session=None ):
	feedback = ntiids.find_object_with_ntiid(oid)
	if feedback is not None:
		submission = get_comment_root( feedback, app_assessment_interfaces.IUsersCourseAssignmentHistoryItem )
		_do_add_feedback( db, nti_session, feedback, submission )
		

def _remove_feedback( db, oid, timestamp=None ):
	feedback = ntiids.find_object_with_ntiid( oid )
	if feedback is not None:
		db.remove_feedback( feedback, timestamp )
		logger.debug("Assignment feedback removed (%s)", feedback )

@component.adapter(app_assessment_interfaces.IUsersCourseAssignmentHistoryItemFeedback,
				   intid_interfaces.IIntIdAddedEvent)
def _feedback_added(feedback, event):
	user = get_creator( feedback )
	nti_session = get_nti_session_id( user )
	process_event( _add_feedback, feedback, nti_session=nti_session )

@component.adapter(app_assessment_interfaces.IUsersCourseAssignmentHistoryItemFeedback,
				   intid_interfaces.IIntIdRemovedEvent)
def _feedback_removed(feedback, event):
	timestamp = datetime.utcnow()
	process_event( _remove_feedback, feedback, nti_session=nti_session, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if assessment_interfaces.IQAssessedQuestionSet.providedBy(obj):
		_process_question_set( obj )
	elif app_assessment_interfaces.IUsersCourseAssignmentHistoryItem.providedBy(obj):
		process_event( _assignment_taken, obj )
	else:
		result = False
	return result
