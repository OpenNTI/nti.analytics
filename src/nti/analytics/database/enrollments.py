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

import zope.intid

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import SessionId
from nti.analytics.identifier import CourseId
_sessionid = SessionId()
_courseid = CourseId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

from nti.analytics.database.meta_mixins import BaseTableMixin
from nti.analytics.database.meta_mixins import BaseViewMixin
from nti.analytics.database.meta_mixins import CourseMixin
from nti.analytics.database.meta_mixins import TimeLengthMixin

from nti.analytics.database.users import get_or_create_user

class CourseCatalogViews(Base,BaseViewMixin,CourseMixin,TimeLengthMixin):
	__tablename__ = 'CourseCatalogViews'

# TODO how will we populate this, at migration time based on client?
# or perhaps statically at first.
class EnrollmentTypes(Base):
	__tablename__ = 'EnrollmentTypes'
	type_id = Column( 'type_id', Integer, Sequence( 'enrollment_type_seq' ), nullable=False, primary_key=True )
	type_name = Column( 'type_name', String(64), nullable=False, index=True, unique=True )

class CourseEnrollments(Base,BaseTableMixin,CourseMixin):
	__tablename__ = 'CourseEnrollments'
	type_id = Column( 'type_id', Integer, ForeignKey( 'EnrollmentTypes.type_id' ), index=True, nullable=False )

class CourseDrops(Base,BaseTableMixin,CourseMixin):
	__tablename__ = 'CourseDrops'

	# Make sure we allow multiple course drops, timestamp should be non-null here.
	__table_args__ = (
        PrimaryKeyConstraint('course_id', 'user_id', 'timestamp'),
    )


def create_course_catalog_view( user, nti_session, timestamp, course, time_length ):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	new_object = CourseCatalogViews( 	user_id=uid,
										session_id=sid,
										timestamp=timestamp,
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

def create_course_enrollment(user, nti_session, timestamp, course, enrollment_type_name):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	enrollment_type = _get_enrollment_type_id( db, enrollment_type_name )
	type_id = enrollment_type.type_id

	new_object = CourseEnrollments( user_id=uid,
									session_id=sid,
									timestamp=timestamp,
									course_id=course_id,
									type_id=type_id )
	db.session.add( new_object )

def create_course_drop(user, nti_session, timestamp, course):
	db = get_analytics_db()
	user = get_or_create_user(user )
	uid = user.user_id
	sid = _sessionid.get_id( nti_session )
	course_id = _courseid.get_id( course )
	timestamp = timestamp_type( timestamp )

	new_object = CourseDrops( 	user_id=uid,
								session_id=sid,
								timestamp=timestamp,
								course_id=course_id )
	db.session.add( new_object )

	enrollment = db.session.query(CourseEnrollments).filter( 	CourseEnrollments.user_id == uid,
															CourseEnrollments.course_id == course_id ).one()
	db.session.delete( enrollment )

