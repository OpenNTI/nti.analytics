#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics_database.resources import Resources

from nti.analytics.database import get_analytics_db

from nti.ntiids import ntiids

logger = __import__('logging').getLogger(__name__)


def _get_resource_display_name(resource_val):
	content_unit = ntiids.find_object_with_ntiid(resource_val)
	display_name = getattr(content_unit, 'label', None)
	return display_name


def _create_resource(db, resource_val, max_time_length):
	display_name = _get_resource_display_name(resource_val)
	new_resource = Resources(resource_ds_id=resource_val,
							 resource_display_name=display_name,
							 max_time_length=max_time_length)

	db.session.add(new_resource)
	db.session.flush()
	return new_resource


def _get_or_create_resource(db, resource_val, max_time_length):
	found_resource = db.session.query(Resources).filter(
									Resources.resource_ds_id == resource_val).first()
	if found_resource is not None:
		# Always update fields (to fix possible issues)
		display_name = _get_resource_display_name(resource_val)
		if display_name:
			found_resource.resource_display_name = display_name
		if max_time_length:
			found_resource.max_time_length = max_time_length
	return found_resource or _create_resource(db, resource_val, max_time_length)


def get_resource_record(db, resource_val, create=False, max_time_length=None):
	"""
	Returns the resource for the given ds resource ntiid.
	"""
	if create:
		resource = _get_or_create_resource(db, resource_val, max_time_length)
	else:
		resource = db.session.query(Resources).filter(
									Resources.resource_ds_id == resource_val).first()
	return resource


def get_resource_id(db, resource_val, create=False, max_time_length=None):
	"""
	Returns the db id for the given ds resource ntiid.
	"""
	resource = get_resource_record(db, resource_val, create, max_time_length)
	return resource.resource_id if resource is not None else None


def get_resource_record_from_id(resource_id):
	"""
	Returns the ds resource for the given db id.
	"""
	db = get_analytics_db()
	resource_record = db.session.query(Resources).filter(
										Resources.resource_id == resource_id).first()
	return resource_record


def get_resource_val(resource_id):
	"""
	Returns the ds resource id (probably ntiid) for the given db id.
	"""
	resource_record = get_resource_record_from_id(resource_id)
	return resource_record and resource_record.resource_ds_id
