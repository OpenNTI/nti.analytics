#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 30.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 30

from zope.component.hooks import setHooks

from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.assessments import AssignmentViews
from nti.analytics.database.assessments import SelfAssessmentViews

from ._utils import do_evolve

TABLES = [ AssignmentViews, SelfAssessmentViews ]

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		# sqlite does not let us alter columns.
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	for table in TABLES:
		op.alter_column( table.__tablename__, 'resource_id', existing_type=Integer, nullable=True )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Make our resource_id column nullable.
	"""
	do_evolve( context, evolve_job, generation )
