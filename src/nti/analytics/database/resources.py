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

from nti.ntiids import ntiids

from nti.analytics.database import get_analytics_db
from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import Base

class Resources(Base):
	__tablename__ = 'Resources'

	resource_id = Column( 'resource_id', Integer, Sequence( 'resource_id_seq' ), index=True, nullable=False, primary_key=True )
	resource_ds_id = Column( 'resource_ds_id', NTIID_COLUMN_TYPE, index=True, nullable=False  )
	resource_display_name = Column( 'resource_display_name', String( 128 ), unique=False, nullable=True )
	# Only applicable for videos
	max_time_length = Column( 'max_time_length', Integer, nullable=True )

def _get_resource_display_name( resource_val ):
	content_unit = ntiids.find_object_with_ntiid( resource_val )
	display_name = getattr( content_unit, 'label', None )
	return display_name

def _create_resource( db, resource_val, max_time_length ):
	display_name = _get_resource_display_name( resource_val )
	new_resource = Resources( 	resource_ds_id=resource_val,
								resource_display_name=display_name,
								max_time_length=max_time_length )

	db.session.add( new_resource )
	db.session.flush()
	return new_resource

def _get_or_create_resource( db, resource_val, max_time_length ):
	found_resource = db.session.query(Resources).filter(
									Resources.resource_ds_id == resource_val ).first()
	if found_resource is not None:
		# Lazy populate fields
		if found_resource.resource_display_name is None:
			found_resource.resource_display_name = _get_resource_display_name( resource_val )
		if found_resource.max_time_length is None:
			found_resource.max_time_length = max_time_length
	return found_resource or _create_resource( db, resource_val, max_time_length )

def get_resource_record( db, resource_val, create=False, max_time_length=None ):
	""" Returns the resource for the given ds resource ntiid. """
	if create:
		resource = _get_or_create_resource( db, resource_val, max_time_length )
	else:
		resource = db.session.query(Resources).filter(
									Resources.resource_ds_id == resource_val ).first()
	return resource

def get_resource_id( db, resource_val, create=False, max_time_length=None ):
	""" Returns the db id for the given ds resource ntiid. """
	resource = get_resource_record( db, resource_val, create, max_time_length )
	return resource.resource_id if resource is not None else None

def get_resource_record_from_id( resource_id ):
	""" Returns the ds resource for the given db id. """
	db = get_analytics_db()
	resource_record = db.session.query( Resources ).filter(
										Resources.resource_id == resource_id ).first()
	return resource_record

def get_resource_val( resource_id ):
	""" Returns the ds resource id (probably ntiid) for the given db id. """
	resource_record = get_resource_record_from_id( resource_id )
	return resource_record and resource_record.resource_ds_id
