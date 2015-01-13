#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 15.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 17

from zope.component.hooks import setHooks

from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db

def do_evolve():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		# sqlite does not let us alter columns.
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	op.alter_column( 'VideoEvents', 'video_end_time', existing_type=Integer, nullable=True )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve(context):
	"""
	Make our video_end_time nullable now that we get video
	start events.
	"""
	do_evolve()
