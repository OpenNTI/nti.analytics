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

from nti.app.products.courseware_ims import get_course_sourcedid

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.analytics.common import get_root_context_name

from nti.analytics.identifier import RootContextId

from nti.analytics.database import Base
from nti.analytics.database import get_analytics_db
from nti.analytics.database import NTIID_COLUMN_TYPE

class RootContext(object):
	"""
	Stores root context objects of other events, such as courses and books.
	"""
	context_id = Column('context_id', Integer, index=True, nullable=False, primary_key=True, autoincrement=False )
	context_ds_id = Column('context_ds_id', NTIID_COLUMN_TYPE, nullable=True, index=True )
	context_name = Column('context_name', String(64), nullable=True, unique=False, index=True)
	context_long_name = Column('context_long_name', NTIID_COLUMN_TYPE, nullable=True)
	start_date = Column('start_date', DateTime, nullable=True)
	end_date = Column('end_date', DateTime, nullable=True)
	# This interval may be represented as time since epoch (e.g. mysql)
	duration = Column('duration', Interval, nullable=True)

class Courses( Base, RootContext ):
	__tablename__ = 'Courses'

	term = Column('term', String(32), nullable=True, unique=False)
	crn = Column('crn', String(32), nullable=True, unique=False)

class Books( Base, RootContext ):
	__tablename__ = 'Books'

class _RootContextId( Base ):
	"A table to share a sequence between our RootContext tables; needed in mysql."
	__tablename__ = 'ContextId'
	# Start at 100 for simple migration.
	context_id = Column('context_id', Integer, Sequence('context_id_seq', start=1000),
						nullable=False, primary_key=True )

def _get_next_id( db ):
	"Return the next id in our pseudo-sequence."
	obj = _RootContextId()
	db.session.add( obj )
	db.session.flush()
	return obj.context_id

def _get_course_long_name( context_object ):
	bundle = getattr( context_object, 'ContentPackageBundle', None )
	context_long_name = getattr( bundle, 'ntiid', None )
	if context_long_name is None:
		# Nothing, try legacy
		context_long_name = getattr( context_object, 'ContentPackageNTIID', None )
	return context_long_name

def _course_catalog( course ):
	try:
		# legacy code path, but faster
		result = course.legacy_catalog_entry
	except AttributeError:
		result = ICourseCatalogEntry( course, None )

	return result

def _create_course( db, course, course_ds_id ):
	context_id = _get_next_id( db )
	course_name = get_root_context_name( course )
	course_long_name = _get_course_long_name( course )
	catalog = _course_catalog( course )
	start_date = getattr( catalog, 'StartDate', None )
	end_date = getattr( catalog, 'EndDate', None )
	duration = getattr( catalog, 'Duration', None )

	course_sid = get_course_sourcedid( course )
	term = getattr( course_sid, 'Term', None )
	crn = getattr( course_sid, 'CRN', None )

	course = Courses( 	context_id=context_id,
						context_ds_id=course_ds_id,
						context_name=course_name,
 						context_long_name=course_long_name,
					 	start_date=start_date,
					 	term=term,
					 	crn=crn,
						end_date=end_date,
						duration=duration )
	# For race conditions, let's just throw since we cannot really handle retrying
	# gracefully at this level. A job-level retry should work though.
	db.session.add( course )
	db.session.flush()
	logger.debug( 	'Created course (course_id=%s) (course_ds_id=%s) (course=%s)',
					course.context_id, course_ds_id, course_name )
	return course

def _get_content_package_long_name( context_object ):
	context_long_name = getattr( context_object, 'ntiid', None )
	return context_long_name

def _create_content_package( db, content_package, context_ds_id ):
	context_id = _get_next_id( db )
	context_name = get_root_context_name( content_package )
	context_long_name = _get_content_package_long_name( content_package )

	book = Books( 	context_id=context_id,
					context_ds_id=context_ds_id,
					context_name=context_name,
 					context_long_name=context_long_name )
	db.session.add( book )
	db.session.flush()
	logger.debug( 	'Created book (context_id=%s) (context_ds_id=%s) (content_package=%s)',
					book.context_id, context_ds_id, context_name )
	return book

def _update_course( course_record, course ):
	# Lazy populate new fields
	if course_record.context_long_name is None:
		course_record.context_long_name = _get_course_long_name( course )

	if 		course_record.start_date is None \
		and course_record.end_date is None \
		and course_record.duration is None:

		catalog = _course_catalog( course )
		course_record.start_date = getattr( catalog, 'StartDate', None )
		course_record.end_date = getattr( catalog, 'EndDate', None )
		course_record.duration = getattr( catalog, 'Duration', None )

	if 		course_record.term is None \
		and course_record.crn is None:

		course_sid = get_course_sourcedid( course )
		course_record.term = getattr( course_sid, 'Term', None )
		course_record.crn = getattr( course_sid, 'CRN', None )


def _get_or_create_course( db, course, context_ds_id ):
	found_course = db.session.query(Courses).filter(
								Courses.context_ds_id == context_ds_id ).first()
	if found_course is not None:
		_update_course( found_course, course )

	return found_course or _create_course( db, course, context_ds_id )

def _get_or_create_content_package( db, context_object, context_ds_id ):
	found_content_package = db.session.query(Books).filter(
										Books.context_ds_id == context_ds_id ).first()
	return found_content_package \
		or _create_content_package( db, context_object, context_ds_id )

def get_root_context_id( db, context_object, create=False ):
	"""
	Retrieves the db id for the given root context object (e.g. course, book),
	optionally creating the context object if it does not exist.
	"""
	context_ds_id = RootContextId.get_id( context_object )
	if create:
		if ICourseInstance.providedBy( context_object ):
			root_context_object = _get_or_create_course( db, context_object, context_ds_id )
		else:
			root_context_object = _get_or_create_content_package( db, context_object, context_ds_id )
	else:
		if ICourseInstance.providedBy( context_object ):
			root_context_object = db.session.query(Courses).filter(
												Courses.context_ds_id == context_ds_id ).first()
		else:
			root_context_object = db.session.query(Books).filter(
												Books.context_ds_id == context_ds_id ).first()
	return root_context_object.context_id if root_context_object is not None else None

def delete_course( context_ds_id ):
	db = get_analytics_db()
	found_course = db.session.query(Courses).filter(
								Courses.context_ds_id == context_ds_id ).first()
	if found_course is not None:
		found_course.context_ds_id = None

def get_root_context( context_id ):
	"Given a database identifier, return the RootContext object."
	db = get_analytics_db()
	result = None
	found_course = db.session.query(Courses).filter( Courses.context_id == context_id,
													Courses.context_ds_id != None ).first()

	if found_course is None:
		found_course = db.session.query(Books).filter( Books.context_id == context_id,
													Books.context_ds_id != None ).first()

	if found_course is not None:
		context_ds_id = found_course.context_ds_id
		result = RootContextId.get_object( context_ds_id )
	return result
