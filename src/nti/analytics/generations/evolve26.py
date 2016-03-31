#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 26.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 26

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.resource_tags import NotesCreated

from .utils import do_evolve

INDEX_EXISTS_QUERY = 	"""
						SHOW INDEX FROM Analytics.%s
						WHERE KEY_NAME = '%s';
						"""

TABLES = [BlogCommentsCreated,
	      ForumCommentsCreated,
	      NotesCreated ]

def _index_exists( con, ix_name, table ):
	res = con.execute( INDEX_EXISTS_QUERY % ( table, ix_name ) )
	return res.scalar()

def evolve_job():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	for table_name in TABLES:
		ix_name = 'ix_%s_parent_user_id' % table_name.__tablename__.lower()
		if not _index_exists( connection, ix_name, table_name.__tablename__ ):
			op.create_index( ix_name, table_name.__tablename__, ['parent_user_id'] )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Add index on parent_user_id column.
	"""
	do_evolve( context, evolve_job, generation )
