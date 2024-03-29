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

from sqlalchemy import String

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics.generations.utils import do_evolve

logger = __import__('logging').getLogger(__name__)

generation = 49

CONVERT_STMT = 'ALTER TABLE Resources CONVERT TO CHARACTER SET utf8;'

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

	# Need to convert existing items before altering column
	connection.execute(CONVERT_STMT)

	op.alter_column('Resources', 'resource_display_name',
					 type_=String(256),
					 existing_type=String(128) )

	logger.info('Finished analytics evolve (%s)', generation)

def evolve( context ):
	"""
	Extend Resources.resource_display_name column
	"""
	do_evolve(context, evolve_job, generation, with_library=False)
