#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics_database.surveys import PollsTaken
from nti.analytics_database.surveys import SurveyViews
from nti.analytics_database.surveys import SurveysTaken

from nti.analytics.common import timestamp_type

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db

from nti.analytics.database.assessments import create_assessment_view

from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.users import get_or_create_user

from nti.analytics.identifier import get_ds_id

logger = __import__('logging').getLogger(__name__)


def _poll_exists(db, submission_id):
	return db.session.query(PollsTaken).filter(
							PollsTaken.submission_id == submission_id).first()


def create_poll_taken(user, nti_session, timestamp, course, submission):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	uid = user_record.user_id
	sid = nti_session
	course_id = get_root_context_id(db, course, create=True)
	timestamp = timestamp_type(timestamp)
	submission_id = get_ds_id(submission)

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
	sid = nti_session
	course_id = get_root_context_id(db, course, create=True)
	timestamp = timestamp_type(timestamp)
	submission_id = get_ds_id(submission)

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


def create_survey_view(user, nti_session, timestamp, course, context_path,
					   resource, time_length, survey_id):
	return create_assessment_view(SurveyViews, user, nti_session, timestamp,
								  course, context_path, resource, time_length,
								  survey_id, 'survey_id')


def _resolve_view(row, course, user):
	if course is not None:
		row.RootContext = course
	if user is not None:
		row.user = user
	return row


def _resolve_survey_view(row, user=None, course=None):
	return _resolve_view(row, course, user)


def get_survey_views(user, course=None, **kwargs):
	"""
	Fetch any survey views for a user created *after* the optionally given
	timestamp. Optionally, can filter by course.
	"""
	results = get_filtered_records(user, SurveyViews,
								   course=course, **kwargs)
	return resolve_objects(_resolve_survey_view, results,
						   user=user, course=course)
