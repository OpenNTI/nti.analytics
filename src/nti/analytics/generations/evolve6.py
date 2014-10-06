#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 6.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 6

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import String

from nti.analytics.database import NTIID_COLUMN_TYPE
from nti.analytics.database import get_analytics_db

def do_evolve(context):
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	connection = db.session.connection()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	op.add_column( "Courses", Column('course_long_name', NTIID_COLUMN_TYPE, nullable=True) )
	op.add_column( "Users", Column('username2', String(64), nullable=True, unique=False) )

	logger.info( 'Finished analytics evolve6' )

def evolve(context):
	"""
	Evolve to generation 6
	"""
	do_evolve(context)
