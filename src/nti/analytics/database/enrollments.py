#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics_database.enrollments import CourseDrops
from nti.analytics_database.enrollments import EnrollmentTypes
from nti.analytics_database.enrollments import CourseEnrollments
from nti.analytics_database.enrollments import CourseCatalogViews

from nti.analytics.common import timestamp_type

from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database._utils import get_context_path

from nti.analytics.database.root_context import get_root_context_id
from nti.analytics.database.root_context import get_root_context_record

from nti.analytics.database.users import get_or_create_user

logger = __import__('logging').getLogger(__name__)


def _course_catalog_view_exists( db, user_id, course_id, timestamp ):
	return db.session.query(CourseCatalogViews ).filter(
							CourseCatalogViews.user_id == user_id,
							CourseCatalogViews.course_id == course_id,
							CourseCatalogViews.timestamp == timestamp ).first()


def create_course_catalog_view(user, nti_session, timestamp, context_path,
							   course, time_length):
	db = get_analytics_db()
	user = get_or_create_user(user)
	sid = nti_session
	course_record = get_root_context_record(db, course, create=True)
	timestamp = timestamp_type( timestamp )

	existing_record = _course_catalog_view_exists(db,
												  user.user_id,
												  course_record.context_id,
												  timestamp)

	if existing_record is not None:
		if should_update_event(existing_record, time_length):
			existing_record.time_length = time_length
			return
		else:
			logger.debug('Course catalog view already exists (user=%s) (catalog=%s) (time_length=%s)',
						 user.user_id,
						 course_record.context_id,
						 time_length)
			return

	context_path = get_context_path( context_path )

	new_object = CourseCatalogViews( session_id=sid,
									 timestamp=timestamp,
									 context_path=context_path,
									 time_length=time_length )
	new_object._course_record = course_record
	new_object._user_record = user
	db.session.add( new_object )


def _create_enrollment_type(db, type_name):
	enrollment_type = EnrollmentTypes(type_name=type_name)
	db.session.add(enrollment_type)
	return enrollment_type


def _get_enrollment_type(db, type_name):
	enrollment_type = db.session.query(EnrollmentTypes).filter(
									   EnrollmentTypes.type_name == type_name).first()
	return enrollment_type or _create_enrollment_type(db, type_name)


def _enrollment_exists( db, user_id, course_id ):
	return db.session.query(CourseEnrollments ).filter(
							CourseEnrollments.user_id == user_id,
							CourseEnrollments.course_id == course_id).count()


def create_course_enrollment(user, nti_session, timestamp, course,
							 enrollment_type_name):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	course_record = get_root_context_record(db, course, create=True)

	if _enrollment_exists(db, user_record.user_id, course_record.context_id):
		logger.debug('Enrollment already exists (user=%s) (course=%s)',
					user, course_record.context_id)
		return

	timestamp = timestamp_type(timestamp)

	enrollment_type = _get_enrollment_type(db, enrollment_type_name)

	new_object = CourseEnrollments(session_id=sid,
								   timestamp=timestamp)
	new_object._user_record = user_record
	new_object._course_record = course_record
	new_object._type_record = enrollment_type
	db.session.add(new_object)
	return new_object


def _course_drop_exists( db, user_id, course_id, timestamp ):
	return db.session.query(CourseDrops ).filter(
							CourseDrops.user_id == user_id,
							CourseDrops.course_id == course_id,
							CourseDrops.timestamp == timestamp).count()


def create_course_drop(user, nti_session, timestamp, course):
	db = get_analytics_db()
	user_record = get_or_create_user(user)
	sid = nti_session
	course_record = get_root_context_record(db, course, create=True)
	timestamp = timestamp_type( timestamp )

	if _course_drop_exists(db, user_record.user_id, course_record.context_id, timestamp):
		logger.debug('Course drop already exists (user=%s) (course=%s)',
					user, course_record.context_id)
		return

	new_object = CourseDrops(session_id=sid,
							 timestamp=timestamp)
	new_object._user_record = user_record
	new_object._course_record = course_record
	db.session.add(new_object)

	db.session.query(CourseEnrollments).filter( CourseEnrollments.user_id == user_record.user_id,
												CourseEnrollments.course_id == course_record.context_id ).delete()


def get_enrollments_for_course( course ):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	enrollments = db.session.query( CourseEnrollments ).filter(
									CourseEnrollments.course_id == course_id ).all()
	return enrollments
