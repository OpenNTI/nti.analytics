#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import BigInteger
from sqlalchemy.ext.declarative import declarative_base

from nti.analytics.database.interfaces import IAnalyticsDB

Base = declarative_base()

SESSION_COLUMN_TYPE = Integer
NTIID_COLUMN_TYPE = String( 256 )
INTID_COLUMN_TYPE = BigInteger

def get_analytics_db():
	return component.getUtility( IAnalyticsDB )

def resolve_objects( to_call, rows, **kwargs ):
	result = ()
	if rows:
		# Resolve the objects, filtering out Nones
		result = [x for x in
					( to_call( row, **kwargs ) for row in rows )
					if x is not None]
	return result

def should_update_event( old_record, new_time_length ):
	"""
	For a record with a 'time_length' field, decide whether the
	event should be updated based on the new time_length given.
	"""
	# We want to update if our new time_length is greater than the old.
	return old_record.time_length < new_time_length
