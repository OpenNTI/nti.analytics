#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 9.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 9

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

UPDATE_RESOURCES_SQL = "ALTER TABLE Resources MODIFY resource_display_name VARCHAR(128) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"
UPDATE_COURSES_SQL = "ALTER TABLE Courses MODIFY course_long_name VARCHAR(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"
UPDATE_COURSES2_SQL = "ALTER TABLE Courses MODIFY course_name VARCHAR(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"

UPDATE_RESOURCE_VIEWS_SQL = "ALTER TABLE CourseResourceViews MODIFY context_path VARCHAR(1048) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"
UPDATE_VIDEO_SQL = "ALTER TABLE VideoEvents MODIFY context_path VARCHAR(1048) CHARACTER SET utf8 COLLATE utf8_unicode_ci;"

SQL_CMDS = [ UPDATE_RESOURCES_SQL, UPDATE_COURSES_SQL, UPDATE_COURSES2_SQL, UPDATE_RESOURCE_VIEWS_SQL, UPDATE_VIDEO_SQL ]

def do_evolve(context):
	setHooks()

	db = get_analytics_db()
	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	# We cannot use our transaction connection since we have
	# implicit commits below.
	connection = db.engine.connect()

	# Fill our new table
	logger.info( 'Changing column character sets' )
	for sql in SQL_CMDS:
		connection.execute( sql )
		db.session.flush()

	logger.info( 'Finished analytics evolve9' )

def evolve(context):
	"""
	Evolve to generation 9
	"""
	do_evolve(context)
