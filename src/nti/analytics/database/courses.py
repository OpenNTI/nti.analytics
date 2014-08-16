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
from sqlalchemy import Boolean
from sqlalchemy import DateTime

from sqlalchemy.schema import Sequence

from nti.analytics.identifier import CourseId
_courseid = CourseId()

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

class Courses(Base):
	__tablename__ = 'Courses'
	course_id = Column('course_id', Integer, Sequence('course_id_seq'), index=True, nullable=False, primary_key=True )
	course_ds_id = Column('course_ds_id', Integer, nullable=True, index=True )

def _create_course( db, course_ds_id ):
	course = Courses( course_ds_id=course_ds_id )
	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add( course )
	db.session.flush()
	logger.debug( 'Created course (course_id=%s) (course_ds_id=%s)', course.course_id, course_ds_id )
	return course

def _get_or_create_course( db, course_ds_id ):
	found_course = db.session.query(Courses).filter( Courses.course_ds_id == course_ds_id ).first()
	return found_course or _create_course( db, course_ds_id )

def get_course_id( db, course ):
	course_ds_id = _courseid.get_id( course )
	course = _get_or_create_course( db, course_ds_id )
	return course.course_id

