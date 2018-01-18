#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 11.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 11

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics.database.resource_views import ResourceViews
from nti.analytics.database.resource_views import VideoEvents
from nti.analytics.database.boards import TopicsViewed
from nti.analytics.database.enrollments import CourseCatalogViews
from nti.analytics.database.blogs import BlogsViewed

VIEW_TABLES = [ ResourceViews, VideoEvents, CourseCatalogViews, TopicsViewed, BlogsViewed ]

def _delete_zero_length_records( db, view_table ):
	deleted_count = db.session.query( view_table ) \
					.filter( view_table.time_length == 0 ) \
					.delete( synchronize_session=False )
	logger.info( 'Deleted zero time length records in %s (deleted_count=%s)', view_table, deleted_count )

def do_evolve(context):
	setHooks()

	db = get_analytics_db()
	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	for view_table in VIEW_TABLES:
		_delete_zero_length_records( db, view_table )

	logger.info( 'Finished analytics evolve11' )

def evolve(context):
	"""
	Evolve to generation 11
	"""
	do_evolve(context)
