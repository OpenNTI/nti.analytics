#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.file.interfaces import IFile

from nti.analytics_database.mime_types import FileMimeTypes

from nti.analytics.database import get_analytics_db

from nti.dataserver.interfaces import ICanvasURLShape

from nti.dataserver.interfaces import ICanvas

logger = __import__('logging').getLogger(__name__)


def get_item_mime_type( obj ):
	try:
		mime_type = obj.contentType
	except AttributeError:
		mime_type = 	getattr( obj, 'mimeType', None ) \
					or 	getattr( obj, 'mime_type', None )
	return mime_type


def _add_mime_type_record( mime_type, mime_dict, db, factory ):
	if mime_type is not None:
		record = mime_dict.get( mime_type )
		if record is None:
			mime_type_record = get_mime_type_record(db, mime_type)
			record = factory( count=0 )
			record._mime_type = mime_type_record
			mime_dict[mime_type] = record
		record.count += 1


def build_mime_type_records( db, obj, factory ):
	"""
	Given an object and a factory, build all the mimetype
	records of `IFile` and `ICanvas` body components.
	"""
	result = ()
	mime_dict = {}
	for item in obj.body or ():
		if IFile.providedBy( item ):
			mime_type = get_item_mime_type( item )
			_add_mime_type_record( mime_type, mime_dict, db, factory )
		elif ICanvas.providedBy( item ):
			# For ICanvas, we want to capture the mime_types of the
			# underlying uploaded files, if available.
			for shape in item.shapeList:
				if ICanvasURLShape.providedBy( shape ):
					# XXX: This is a lot of knowledge.
					shape_obj = getattr( shape, '_file', None )
					mime_type = get_item_mime_type( shape_obj )
					_add_mime_type_record( mime_type, mime_dict, db, factory )
	if mime_dict:
		result = mime_dict.values()
	return result


def get_mime_type_record(db, mime_type, create=True):
	"""
	Get the mime type database id, optionally creating it.
	"""
	result = db.session.query(FileMimeTypes).filter(
							  FileMimeTypes.mime_type == mime_type).first()
	if result is None and create:
		result = FileMimeTypes( mime_type=mime_type )
		db.session.add(result)
	return result


def get_mime_type_id(db, mime_type, create=True):
	"""
	Get the mime type database id, optionally creating it.
	"""
	result = get_mime_type_record(db, mime_type, create)
	return result and result.file_mime_type_id


def get_all_mime_types():
	"""
	Return a set of all mime_types in the db.
	"""
	db = get_analytics_db()
	results = db.session.query(FileMimeTypes).all()
	return {x.mime_type for x in results}
