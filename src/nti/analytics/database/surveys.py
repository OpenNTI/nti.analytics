#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from sqlalchemy import Column
from sqlalchemy import Integer

from sqlalchemy.schema import Sequence

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import SubmissionId

from nti.analytics.database.users import get_or_create_user

from nti.analytics.database import Base
from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import CourseMixin

from nti.analytics.database.root_context import get_root_context_id

class InquiryMixin(BaseTableMixin,CourseMixin):
	pass

class PollsTaken(Base,InquiryMixin):
	__tablename__ = 'PollsTaken'
	submission_id = Column('submission_id', INTID_COLUMN_TYPE, nullable=True,
						index=True, autoincrement=False )

	poll_taken_id = Column('poll_taken_id', Integer, Sequence( 'poll_taken_seq' ),
								index=True, nullable=False, primary_key=True )

	poll_id = Column('poll_id', NTIID_COLUMN_TYPE, nullable=False, index=True )

class SurveysTaken(Base,InquiryMixin):
	__tablename__ = 'SurveysTaken'
	submission_id = Column('submission_id', INTID_COLUMN_TYPE, nullable=True,
						index=True, autoincrement=False )

	survey_taken_id = Column('survey_taken_id', Integer, Sequence( 'survey_taken_seq' ),
								index=True, nullable=False, primary_key=True )

	survey_id = Column('survey_id', NTIID_COLUMN_TYPE, nullable=False, index=True )

def _poll_exists( db, submission_id ):
	return db.session.query( PollsTaken ).filter(
					PollsTaken.submission_id == submission_id ).first()

def create_poll_taken( user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )
	submission_id = SubmissionId.get_id( submission )

	if _poll_exists( db, submission_id ):
		logger.warn( "Poll already exists (ds_id=%s) (user=%s) ",
					submission_id, user )
		return False

	new_object = PollsTaken( user_id=uid,
							session_id=sid,
							timestamp=timestamp,
							course_id=course_id,
							poll_id=submission.inquiryId,
							submission_id=submission_id )
	db.session.add( new_object )
	db.session.flush()
	return new_object

def _survey_exists( db, submission_id ):
	return db.session.query( SurveysTaken ).filter(
					SurveysTaken.submission_id == submission_id ).first()

def create_survey_taken( user, nti_session, timestamp, course, submission ):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )
	submission_id = SubmissionId.get_id( submission )

	if _survey_exists( db, submission_id ):
		logger.warn( "Survey already exists (ds_id=%s) (user=%s) ",
					submission_id, user )
		return False

	new_object = SurveysTaken( user_id=uid,
							session_id=sid,
							timestamp=timestamp,
							course_id=course_id,
							survey_id=submission.inquiryId,
							submission_id=submission_id )
	db.session.add( new_object )
	db.session.flush()
	return new_object
