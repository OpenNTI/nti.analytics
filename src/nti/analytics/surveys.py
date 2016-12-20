#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zc.intid.interfaces import IAfterIdAddedEvent

from nti.app.assessment.interfaces import IUsersCourseInquiryItem

from nti.assessment.interfaces import IQPoll
from nti.assessment.interfaces import IQSurvey

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.analytics.sessions import get_nti_session_id

from . import get_factory
from . import ASSESSMENTS_ANALYTICS

from .common import get_course
from .common import get_creator
from .common import process_event
from .common import get_created_timestamp

from .database import surveys as db_surveys

from .interfaces import IObjectProcessor

component.moduleProvides(IObjectProcessor)

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue(ASSESSMENTS_ANALYTICS)

def _get_course( submission ):
	course = get_course( submission )
	if course is None:
		raise TypeError( 'No course found for submission (%s)', submission )

	return course

def _process_poll( submission, nti_session=None ):
	user = get_creator( submission )
	timestamp = get_created_timestamp( submission )
	course = _get_course( submission )
	db_surveys.create_poll_taken(user, nti_session,
								timestamp, course, submission)
	logger.debug("Poll submitted (user=%s) (id=%s)",
				 user, submission.inquiryId )

def _process_survey( submission, nti_session=None ):
	user = get_creator( submission )
	timestamp = get_created_timestamp( submission )
	course = _get_course( submission )
	db_surveys.create_survey_taken(user, nti_session,
								timestamp, course, submission)
	logger.debug("Survey submitted (user=%s) (id=%s)",
				 user, submission.inquiryId )

def _process_inquiry( oid, nti_session):
	submission = find_object_with_ntiid( oid )
	if submission is not None:
		inquiry = submission.Inquiry
		if IQPoll.providedBy( inquiry ):
			_process_poll( submission, nti_session )
		elif IQSurvey.providedBy( inquiry ):
			_process_survey( submission, nti_session )

@component.adapter(IUsersCourseInquiryItem, IAfterIdAddedEvent)
def _inquiry_taken( inquiry, event ):
	nti_session = get_nti_session_id()
	process_event( _get_job_queue, _process_inquiry, inquiry, nti_session=nti_session )

def init( obj ):
	result = True
	if IUsersCourseInquiryItem.providedBy(obj):
		process_event( _get_job_queue, _process_inquiry, obj )
	else:
		result = False
	return result
