#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 44.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 44

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import String

from nti.analytics.database import get_analytics_db

from nti.analytics.generations.utils import do_evolve

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
	seen_dbs.add( db.dburi )

	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	op.alter_column( 'SearchQueries', 'search_types',
					  type_=String(1024),
					  existing_type=String(256) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Expand our mime_type column to 128 chars.
	"""
	do_evolve( context, evolve_job, generation, with_library=False )
