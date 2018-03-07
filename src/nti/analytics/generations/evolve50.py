#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 45.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from alembic.operations import Operations
from alembic.migration import MigrationContext

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics.generations.utils import do_evolve

logger = __import__('logging').getLogger(__name__)

generation = 50

seen = set()
seen_dbs = set()

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Not sure why this is needed; we would deadlock if we attempt
	# alter_columns on the same db.
	global seen_dbs
	if db.dburi in seen_dbs:
		return
	seen_dbs.add(db.dburi)

	connection = db.engine.connect()
	mc = MigrationContext.configure(connection)
	op = Operations(mc)

	op.drop_column('IpGeoLocation', 'latitude')
	op.drop_column('IpGeoLocation', 'longitude')

	logger.info('Finished analytics evolve (%s)', generation)

def evolve( context ):
	"""
	Drop duplicate columns
	"""
	do_evolve(context, evolve_job, generation, with_library=False)
