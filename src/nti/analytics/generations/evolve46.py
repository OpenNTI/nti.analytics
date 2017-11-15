#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 45.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 46

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
	# XXX: This migration had weird issues in alpha (hanging tx issues).
	# a db restart resolved it.
	global seen_dbs
	if db.dburi in seen_dbs:
		return
	seen_dbs.add( db.dburi )

	connection = db.engine.connect()
	mc = MigrationContext.configure(connection)
	op = Operations(mc)

	op.alter_column( 'Users', 'username',
					  type_=String(128),
					  existing_type=String(64) )
	op.alter_column( 'Users', 'username2',
					  type_=String(128),
					  existing_type=String(64) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Expand our username column to 128 chars.
	"""
	do_evolve( context, evolve_job, generation, with_library=False )
