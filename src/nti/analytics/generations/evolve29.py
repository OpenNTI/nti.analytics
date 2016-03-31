#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 25.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 29

from zope.component.hooks import setHooks

from sqlalchemy import Column

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import get_analytics_db
from nti.analytics.database.assessments import AssignmentViews
from nti.analytics.database.assessments import SelfAssessmentViews

from .utils import do_evolve
from .utils import mysql_column_exists

TABLES = [ AssignmentViews, SelfAssessmentViews ]

def evolve_job():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	# Add our column
	for table in TABLES:
		if not mysql_column_exists( connection, table.__tablename__, 'assignment_id' ):
			op.add_column( table.__tablename__,
						Column('assignment_id', NTIID_COLUMN_TYPE, nullable=False, index=True ) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Add 'assignment_id' column to assessment view tables.
	"""
	do_evolve( context, evolve_job, generation )
