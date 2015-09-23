#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics_database.surveys import PollsTaken
from nti.analytics_database.surveys import SurveysTaken

from ..common import timestamp_type

from ..identifier import SessionId
from ..identifier import SubmissionId

from .root_context import get_root_context_id

from .users import get_or_create_user

from . import get_analytics_db

def _poll_exists(db, submission_id):
	return db.session.query(PollsTaken).filter(
					PollsTaken.submission_id == submission_id).first()

def create_poll_taken(user, nti_session, timestamp, course, submission):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	uid = user_record.user_id
	sid = SessionId.get_id(nti_session)
	course_id = get_root_context_id(db, course, create=True)
	timestamp = timestamp_type(timestamp)
	submission_id = SubmissionId.get_id(submission)

	if _poll_exists(db, submission_id):
		logger.warn("Poll already exists (ds_id=%s) (user=%s) ",
					submission_id, user)
		return False

	new_object = PollsTaken(user_id=uid,
							session_id=sid,
							timestamp=timestamp,
							course_id=course_id,
							poll_id=submission.inquiryId,
							submission_id=submission_id)
	db.session.add(new_object)
	db.session.flush()
	return new_object

def _survey_exists(db, submission_id):
	return db.session.query(SurveysTaken).filter(
					SurveysTaken.submission_id == submission_id).first()

def create_survey_taken(user, nti_session, timestamp, course, submission):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	uid = user_record.user_id
	sid = SessionId.get_id(nti_session)
	course_id = get_root_context_id(db, course, create=True)
	timestamp = timestamp_type(timestamp)
	submission_id = SubmissionId.get_id(submission)

	if _survey_exists(db, submission_id):
		logger.warn("Survey already exists (ds_id=%s) (user=%s) ",
					submission_id, user)
		return False

	new_object = SurveysTaken(user_id=uid,
							  session_id=sid,
							  timestamp=timestamp,
							  course_id=course_id,
							  survey_id=submission.inquiryId,
							  submission_id=submission_id)
	db.session.add(new_object)
	db.session.flush()
	return new_object
