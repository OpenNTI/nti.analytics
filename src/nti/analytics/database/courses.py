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
from sqlalchemy import DateTime
from sqlalchemy import Interval

from sqlalchemy.schema import Sequence

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.analytics.common import get_course_name

from nti.analytics.identifier import CourseId

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import INTID_COLUMN_TYPE

class Courses(Base):
	__tablename__ = 'Courses'
	course_id = Column('course_id', Integer, Sequence('course_id_seq'), index=True, nullable=False, primary_key=True )
	course_ds_id = Column('course_ds_id', INTID_COLUMN_TYPE, nullable=True, index=True )
	course_name = Column('course_name', String(64), nullable=True, unique=False, index=True)
	course_long_name = Column('course_long_name', NTIID_COLUMN_TYPE, nullable=True)
	start_date = Column('start_date', DateTime, nullable=True)
	end_date = Column('end_date', DateTime, nullable=True)
	# This interval may be represented as time since epoch (e.g. mysql)
	duration = Column('duration', Interval, nullable=True)

def _get_course_long_name( course ):
	bundle = getattr( course, 'ContentPackageBundle', None )
	course_long_name = getattr( bundle, 'ntiid', None )
	if course_long_name is None:
		# Nothing, try legacy
		course_long_name = getattr( course, 'ContentPackageNTIID', None )
	return course_long_name

def _course_catalog( course ):
	try:
		# legacy code path, but faster
		result = course.legacy_catalog_entry
	except AttributeError:
		result = ICourseCatalogEntry( course, None )

	return result

def _create_course( db, course, course_ds_id ):
	course_name = get_course_name( course )
	course_long_name = _get_course_long_name( course )
	catalog = _course_catalog( course )
	start_date = getattr( catalog, 'StartDate', None )
	end_date = getattr( catalog, 'EndDate', None )
	duration = getattr( catalog, 'Duration', None )

	course = Courses( 	course_ds_id=course_ds_id,
						course_name=course_name,
 						course_long_name=course_long_name,
						start_date=start_date,
						end_date=end_date,
						duration=duration )
	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add( course )
	db.session.flush()
	logger.debug( 	'Created course (course_id=%s) (course_ds_id=%s) (course=%s)',
					course.course_id, course_ds_id, course_name )
	return course

def _get_or_create_course( db, course, course_ds_id ):
	found_course = db.session.query(Courses).filter( Courses.course_ds_id == course_ds_id ).first()
	if found_course is not None:

		# Lazy populate new fields
		if found_course.course_long_name is None:
			found_course.course_long_name = _get_course_long_name( course )

		if 		found_course.start_date is None \
			and found_course.end_date is None \
			and found_course.duration is None:

			catalog = _course_catalog( course )
			found_course.start_date = getattr( catalog, 'StartDate', None )
			found_course.end_date = getattr( catalog, 'EndDate', None )
			found_course.duration = getattr( catalog, 'Duration', None )

	return found_course or _create_course( db, course, course_ds_id )

def get_course_id( db, course, create=False ):
	""" Retrieves the db id for the given course, optionally creating the course if it does not exist. """
	course_ds_id = CourseId.get_id( course )
	if create:
		found_course = _get_or_create_course( db, course, course_ds_id )
	else:
		found_course = db.session.query(Courses).filter( Courses.course_ds_id == course_ds_id ).first()
	return found_course.course_id if found_course is not None else None

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
