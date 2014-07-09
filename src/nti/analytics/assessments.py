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

# # Questions
# def _get_creator_in_lineage(obj):
# 	result = None
# 	while result is None and obj is not None:
# 		result = get_creator(obj)
# 		obj = getattr(obj, '__parent__', None)
# 		if nti_interfaces.IUser.providedBy(obj) and result is None:
# 			result = obj
# 	return result
# 
# def _get_underlying(obj):
# 	if 	assessment_interfaces.IQuestion.providedBy(obj) or \
# 		assessment_interfaces.IQuestionSet.providedBy(obj) or \
# 		assessment_interfaces.IQAssignment.providedBy(obj) :
# 		result = obj
# 	elif assessment_interfaces.IQAssessedQuestion.providedBy(obj):
# 		result = component.getUtility(assessment_interfaces.IQuestion,
# 									  name=obj.questionId)
# 	elif assessment_interfaces.IQAssessedQuestionSet.providedBy(obj):
# 		result = component.getUtility(assessment_interfaces.IQuestionSet,
# 									  name=obj.questionSetId)
# 	else:
# 		result = None # Throw Exception?
# 	return result


def _do_assess_question( db, question, nti_session ):
	pass

def _assess_question( db, oid, nti_session=None ):
	question = ntiids.find_object_with_ntiid(oid)
	if question is not None:
		_do_assess_question( db, question, nti_session)

def _assess_question_set( db, oid, nti_session=None, time_length=None ):
	submission = ntiids.find_object_with_ntiid( oid )
	if submission is not None:
		user = get_creator( submission )
		timestamp = get_created_timestamp( submission )
		course = get_course_by_ntiid( submission.containerId )
		db.create_self_assessment_taken( user, nti_session, timestamp, course, time_length, submission )
		logger.debug("Self-assessment submitted (user=%s) (assignment=%s)", user, submission.questionSetId )
	# See if this is an assignment 
# 	containerId = question_set.containerId
# 	container = ntiids.find_object_with_ntiid( containerId )
# 	assignment = IQAssignment( container )
	
	# Are these only self-assessments?
# 	if question_set is not None:
# 		for question in question_set.questions:
# 			_do_assess_question( db, question, nti_session )
		

@component.adapter(assessment_interfaces.IQAssessedQuestionSet,
				   intid_interfaces.IIntIdAddedEvent)
def _questionset_assessed( question_set, event ):
	user = get_creator( question_set )
	nti_session = get_nti_session_id( user )
	process_event( _assess_question_set, question_set, nti_session=nti_session )

@component.adapter(assessment_interfaces.IQAssessedQuestion,
				   intid_interfaces.IIntIdAddedEvent)
def _question_assessed( question, event ):
	user = get_creator( question )
	nti_session = get_nti_session_id( user )
	process_event( _assess_question, question, nti_session=nti_session )

# Assignments
# TODO time-length
def _assignment_taken( db, oid, nti_session=None, time_length=None ):
	# TODO How can we distinguish between auto-graded items and not-yet graded items?
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

def _set_grade( db, oid, nti_session=None ):
	grade = ntiids.find_object_with_ntiid(oid)
	if grade is not None:
		user = get_creator( grade )
		db.set_grade( user, nti_session, grade )
		assignment_id = getattr( grade, 'AssignmentId', None )
		logger.debug( 	"Setting grade for assignment (user=%s) (grade=%s) (assignment=%s)", 
						user, 
						grade,
						assignment_id )

@component.adapter(grade_interfaces.IGrade,
				   lce_interfaces.IObjectModifiedEvent)
def _grade_modified(grade, event):
	user = get_creator( grade )
	nti_session = get_nti_session_id( user )
	process_event( _set_grade, grade, nti_session=nti_session )

@component.adapter(grade_interfaces.IGrade,
				   intid_interfaces.IIntIdAddedEvent)
def _grade_added(grade, event):
	_grade_modified( grade, event )

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

# utils
# 
# def get_course_enrollments(user):
# 	container = []
# 	subs = component.subscribers((user,), course_interfaces.IPrincipalEnrollmentCatalog)
# 	for catalog in subs:
# 		queried = catalog.iter_enrollments()
# 		container.extend(queried)
# 	container[:] = [course_interfaces.ICourseInstanceEnrollment(x) for x in container]
# 	return container

def _add_submission( db, oid, timestamp=None ):
	pass

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	result = True
	if 	assessment_interfaces.IQAssessedQuestion.providedBy(obj):
		from IPython.core.debugger import Tracer;Tracer()()
		process_event( _assess_question, obj )
	elif assessment_interfaces.IQAssessedQuestionSet.providedBy(obj):
		# (only?) Self-assessments
		# TODO Hmm, we may not have details here for self-assessments
		# FIXME Distinguishing between self-assessments and assignments may be a pain:
		# traversing course objects (just like in the reports).  
		# See if things have improved recently.
		process_event( _assess_question_set, obj )
	elif app_assessment_interfaces.IUsersCourseAssignmentHistoryItem.providedBy(obj):
		process_event( _assignment_taken, obj )
	else:
		result = False
	return result
