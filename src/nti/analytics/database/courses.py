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

from sqlalchemy.schema import Sequence

from nti.analytics.common import get_course_name

from nti.analytics.identifier import CourseId

from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import INTID_COLUMN_TYPE
from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db

class Courses(Base):
	__tablename__ = 'Courses'
	course_id = Column('course_id', Integer, Sequence('course_id_seq'), index=True, nullable=False, primary_key=True )
	course_ds_id = Column('course_ds_id', INTID_COLUMN_TYPE, nullable=True, index=True )
	course_name = Column('course_name', String(64), nullable=True, unique=False, index=True)
	course_long_name = Column('course_long_name', NTIID_COLUMN_TYPE, nullable=True)

def _get_course_long_name( course ):
	bundle = getattr( course, 'ContentPackageBundle', None )
	course_long_name = getattr( bundle, 'ntiid', None )

	if course_long_name is None:
		# Nothing, try legacy
		course_long_name = getattr( course, 'ContentPackageNTIID', None )

	return course_long_name

def _create_course( db, course, course_ds_id ):
	course_name = get_course_name( course )
	course_long_name = _get_course_long_name( course )
	course = Courses( 	course_ds_id=course_ds_id,
						course_name=course_name,
						course_long_name=course_long_name )
	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add( course )
	db.session.flush()
	logger.debug( 'Created course (course_id=%s) (course_ds_id=%s) (course=%s)', course.course_id, course_ds_id, course_name )
	return course

def _get_or_create_course( db, course, course_ds_id ):
	found_course = db.session.query(Courses).filter( Courses.course_ds_id == course_ds_id ).first()
	if found_course is not None:
		if found_course.course_long_name is None:
			# Lazy populate new field
			found_course.course_long_name = _get_course_long_name( course )
	return found_course or _create_course( db, course, course_ds_id )

def get_course_id( db, course ):
	course_ds_id = CourseId.get_id( course )
	course = _get_or_create_course( db, course, course_ds_id )
	return course.course_id

def delete_course( course_ds_id ):
	db = get_analytics_db()
	found_course = db.session.query(Courses).filter( Courses.course_ds_id == course_ds_id ).first()
	if found_course is not None:
		found_course.course_ds_id = None

def get_course( course_id ):
	db = get_analytics_db()
	result = None
	found_course = db.session.query(Courses).filter( Courses.course_id == course_id,
													Courses.course_ds_id != None ).first()
	if found_course is not None:
		course_ds_id = found_course.course_ds_id
		result = CourseId.get_object( course_ds_id )
	return result
