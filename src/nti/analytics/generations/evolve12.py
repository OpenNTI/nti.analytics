#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 12.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 12

from zope import component
from zope.component.hooks import site
from zope.component.hooks import setHooks
from zope.intid.interfaces import IIntIds

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import DateTime

from nti.analytics.database import get_analytics_db

def do_evolve( intids ):
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	op.add_column( "Courses", Column('start_date', DateTime, nullable=True) )
	op.add_column( "Courses", Column('end_date', DateTime, nullable=True) )
	op.add_column( "Courses", Column('duration', String(32), nullable=True) )

	op.add_column( "Users", Column('create_date', DateTime, nullable=True) )

	logger.info( 'Finished analytics evolve12' )

def evolve(context):
	"""
	Evolve to generation 12
	"""
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		intids = component.getUtility( IIntIds )
		do_evolve( intids )
