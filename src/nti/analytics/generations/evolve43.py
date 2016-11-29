#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 43.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 43

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics_database.resource_views import VideoEvents

from nti.analytics.generations.utils import do_evolve

seen_dbs = set()

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	global seen_dbs
	if db.dburi in seen_dbs:
		return
	seen_dbs.add( db.dburi )
	logger.info( 'Updating %s', db.dburi )

	# Update sharing
	# This may be wonky in alpha since we have one db for all sites.
	updated_count = 0

	for record in db.session.query( VideoEvents ).filter( VideoEvents.time_length == None,
														  VideoEvents.video_start_time is not None,
														  VideoEvents.video_end_time is not None,
														  VideoEvents.video_end_time > 0 ).all():
		updated_count += 1
		record.time_length = abs( record.video_start_time - record.video_end_time )

	logger.info( 'Finished analytics evolve (%s) (updated=%s)', generation, updated_count )

def evolve( context ):
	"""
	Fix video watches missing time_length info.
	"""
	do_evolve( context, evolve_job, generation, with_library=False )
