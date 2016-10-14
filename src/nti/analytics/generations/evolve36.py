#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 33.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 36

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Enum

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics.database.resource_tags import _get_sharing_enum

from nti.analytics.database.root_context import get_root_context

from nti.analytics_database.resource_tags import NotesCreated
from nti.analytics_database.resource_tags import SHARING_ENUMS

from nti.analytics.identifier import get_ds_object

from nti.analytics.generations.utils import do_evolve

UPDATE_SHARING_SQL = """UPDATE NotesCreated
						SET sharing = 'Other'
						WHERE sharing = ' ';"""

seen = set()
seen_dbs = set()

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Not sure why this is needed; we would deadlock if we attempt
	# alter_columns on the same db.
	global seen_dbs
	if db.dburi in seen_dbs:
		return
	logger.info( 'Updating %s', db.dburi )
	seen_dbs.add( db.dburi )

	# First have to make sure our column has correct data, then we have to fix it.
	logger.info( 'Updating broken sharing records' )
	connection = db.engine.connect()
	connection.execute( UPDATE_SHARING_SQL )

	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	logger.info( 'Updating enum column validation' )
	# Now update our enum columns to validate on insert.
	op.alter_column( 'NotesCreated', 'sharing',
					  type_=SHARING_ENUMS,
					  existing_type=Enum('GLOBAL', 'PRIVATE_COURSE', 'PUBLIC_COURSE', 'PRIVATE', 'OTHER') )
	op.alter_column( 'VideoEvents', 'video_event_type',
					 type_=Enum('WATCH', 'SKIP', validate_strings=True),
					 existing_type=Enum('WATCH', 'SKIP') )

	logger.info( 'Updating sharing records' )
	global seen
	# Update sharing
	# This may be wonky in alpha since we have one db for all sites.
	updated_count = 0
	for record in db.session.query( NotesCreated ).yield_per( 1000 ):
		if record.course_id is None or record.note_ds_id is None:
			continue

		if record.note_ds_id in seen:
			continue

		course = get_root_context( record.course_id )
		if course is None:
			continue

		note = get_ds_object( record.note_ds_id )
		if note is None:
			continue

		# Add to our cache so we don't check this object for
		# other sites
		seen.add( record.note_ds_id )

		sharing = _get_sharing_enum(note, course)
		record.sharing = sharing
		updated_count += 1
		if updated_count % 500 == 0:
			logger.info( 'Updated %s records', updated_count )

	logger.info( 'Finished analytics evolve (%s) (updated=%s)', generation, updated_count )

def evolve( context ):
	"""
	Expand and correct the sharing scope information in notes.
	"""
	do_evolve( context, evolve_job, generation, with_library=True )
