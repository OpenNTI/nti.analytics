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
from sqlalchemy import String
from sqlalchemy import ForeignKey

from sqlalchemy.schema import Sequence
from sqlalchemy.schema import PrimaryKeyConstraint

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import should_update_event

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import CourseMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database.users import get_or_create_user
from nti.analytics.database.root_context import get_root_context_id

from nti.analytics.database._utils import get_context_path

class CourseCatalogViews(Base,BaseViewMixin,CourseMixin,TimeLengthMixin):
	__tablename__ = 'CourseCatalogViews'

	__table_args__ = (
        PrimaryKeyConstraint('user_id', 'course_id', 'timestamp'),
    )

class EnrollmentTypes(Base):
	__tablename__ = 'EnrollmentTypes'
	type_id = Column( 'type_id', Integer, Sequence( 'enrollment_type_seq' ), nullable=False, primary_key=True )
	type_name = Column( 'type_name', String(64), nullable=False, index=True, unique=True )

class CourseEnrollments(Base,BaseTableMixin,CourseMixin):
	__tablename__ = 'CourseEnrollments'
	type_id = Column( 'type_id', Integer, ForeignKey( 'EnrollmentTypes.type_id' ), index=True, nullable=False )

	__table_args__ = (
        PrimaryKeyConstraint('course_id', 'user_id'),
    )

class CourseDrops(Base,BaseTableMixin,CourseMixin):
	__tablename__ = 'CourseDrops'

	# Make sure we allow multiple course drops, timestamp should be non-null here.
	__table_args__ = (
        PrimaryKeyConstraint('course_id', 'user_id', 'timestamp'),
    )

def _course_catalog_view_exists( db, user_id, course_id, timestamp ):
	return db.session.query( CourseCatalogViews ).filter(
							CourseCatalogViews.user_id == user_id,
							CourseCatalogViews.course_id == course_id,
							CourseCatalogViews.timestamp == timestamp ).first()

def create_course_catalog_view( user, nti_session, timestamp, context_path, course, time_length ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	existing_record = _course_catalog_view_exists( db, uid, course_id, timestamp )

	if existing_record is not None:
		if should_update_event( existing_record, time_length ):
			existing_record.time_length = time_length
			return
		else:
			logger.warn( 'Course catalog view already exists (user=%s) (catalog=%s)',
						uid, course_id )
			return

	context_path = get_context_path( context_path )

	new_object = CourseCatalogViews( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
										context_path=context_path,
										course_id=course_id,
										time_length=time_length )
	db.session.add( new_object )

def _create_enrollment_type(db, type_name):
	enrollment_type = EnrollmentTypes( type_name=type_name )
	db.session.add( enrollment_type )
	db.session.flush()
	return enrollment_type

def _get_enrollment_type_id(db, type_name):
	enrollment_type = db.session.query(EnrollmentTypes).filter( EnrollmentTypes.type_name == type_name ).first()
	return enrollment_type or _create_enrollment_type( db, type_name )

def _enrollment_exists( db, user_id, course_id ):
	return db.session.query( CourseEnrollments ).filter(
							CourseEnrollments.user_id == user_id,
							CourseEnrollments.course_id == course_id ).count()

def create_course_enrollment(user, nti_session, timestamp, course, enrollment_type_name):
	db = get_analytics_db()

	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_root_context_id( db, course, create=True )

	if _enrollment_exists( db, uid, course_id ):
		logger.warn( 'Enrollment already exists (user=%s) (course=%s)',
					user, course_id )
		return

	timestamp = timestamp_type( timestamp )

	enrollment_type = _get_enrollment_type_id( db, enrollment_type_name )
	type_id = enrollment_type.type_id

	new_object = CourseEnrollments( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									type_id=type_id )
	db.session.add( new_object )

def _course_drop_exists( db, user_id, course_id, timestamp ):
	return db.session.query( CourseDrops ).filter(
							CourseDrops.user_id == user_id,
							CourseDrops.course_id == course_id,
							CourseDrops.timestamp == timestamp ).count()

def create_course_drop(user, nti_session, timestamp, course):
	db = get_analytics_db()
	user_record = get_or_create_user( user )
	uid = user_record.user_id
	sid = SessionId.get_id( nti_session )
	course_id = get_root_context_id( db, course, create=True )
	timestamp = timestamp_type( timestamp )

	if _course_drop_exists( db, uid, course_id, timestamp ):
		logger.warn( 'Course drop already exists (user=%s) (course=%s)',
					user, course_id )
		return

	new_object = CourseDrops( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id )
	db.session.add( new_object )

	db.session.query(CourseEnrollments).filter( CourseEnrollments.user_id == uid,
												CourseEnrollments.course_id == course_id ).delete()

def get_enrollments_for_course( course ):
	db = get_analytics_db()
	course_id = get_root_context_id( db, course )
	enrollments = db.session.query( CourseEnrollments ).filter(
									CourseEnrollments.course_id == course_id ).all()
	return enrollments
