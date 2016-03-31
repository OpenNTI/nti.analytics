#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 35.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 35

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db

from nti.analytics_database.resource_tags import SHARING_ENUMS

from .utils import do_evolve

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	# Adjust our enum
	op.alter_column( 'NotesCreated', 'sharing', type_=SHARING_ENUMS, nullable=True )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Expand our sharing possibilities.
	"""
	do_evolve( context, evolve_job, generation, with_library=True )
