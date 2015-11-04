#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 37.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 37

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from ._utils import do_evolve

UPDATE_CITY_SQL = """ALTER TABLE Location
					MODIFY city VARCHAR(64) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"""

UPDATE_STATE_SQL = """ALTER TABLE Location
					MODIFY state VARCHAR(64) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"""

UPDATE_COUNTRY_SQL = """ALTER TABLE Location
					MODIFY country VARCHAR(64) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"""

SQL_CMDS = [ UPDATE_CITY_SQL, UPDATE_STATE_SQL, UPDATE_COUNTRY_SQL ]

def evolve_job():
	setHooks()

	db = get_analytics_db()
	if db.defaultSQLite:
		return

	# We cannot use our transaction connection since we have
	# implicit commits below.
	connection = db.engine.connect()

	for sql in SQL_CMDS:
		connection.execute( sql )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve(context):
	"""
	Make location columns utf-8.
	We should make these mysql databases utf-8 at create time.
	"""
	do_evolve( context, evolve_job, generation )
