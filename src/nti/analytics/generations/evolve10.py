#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 8.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 10

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db
from nti.analytics.database.resources import Resources

from nti.analytics.database.resource_views import CourseResourceViews
from nti.analytics.database.resource_views import VideoEvents
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NotesViewed
from nti.analytics.database.resource_tags import HighlightsCreated

FOREIGN_TABLES = [ CourseResourceViews, VideoEvents, NotesCreated, NotesViewed, HighlightsCreated]

def _fix_references( db, foreign_table, bad_values ):
	logger.info( 'Fixing references in foreign key table (%s)', foreign_table )
	results = db.session.query( foreign_table, Resources ) \
						.join( Resources ) \
						.filter( foreign_table.resource_id.in_( bad_values ) ).all()

	total_count = len( results )
	updated_count = 0

	for result in results:
		foreign_record, resource_record = result
		resource_ds_id = resource_record.resource_ds_id
		try:
			# Ok, our ntiid val is actually an int
			# Move it over so we can delete the mucked up
			# record in the Resources table.

			# This value should now reference a valid ntiid.
			correct_resource_id = int( resource_ds_id )
			foreign_record.resource_id = correct_resource_id
			updated_count += 1
		except ValueError:
			pass

	# Sanity check counts match
	logger.info( 'Finished fixing references in foreign key table (%s) (count=%s) (expected=%s)',
				foreign_table, updated_count, total_count )

def _remove_invalid_records( db ):
	# Remove all int values from Resources table due to
	# double migration.
	all_resources = db.session.query( Resources ).all()
	delete_count = 0
	bad_values = []
	total_count = len( all_resources )

	for resource_record in all_resources:
		resource_ds_id = resource_record.resource_ds_id
		try:
			int( resource_ds_id )
			bad_values.append( resource_record.resource_id )
			delete_count += 1
		except ValueError:
			# Good record
			pass

	logger.info( 'Found bad records in Resources table (total=%s) (dropped_records=%s)',
				total_count, delete_count )
	return bad_values

def _delete_from_resources( db, bad_values ):
	logger.info( 'Removing invalid records in Resources table' )
	deleted_count = db.session.query( Resources ) \
					.filter( Resources.resource_id.in_( bad_values ) ) \
					.delete( synchronize_session=False )
	logger.info( 'Finished evolve10 (deleted_count=%s)', deleted_count )

def do_evolve(context):
	setHooks()

	db = get_analytics_db()
	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	# Gather our bad values
	bad_values = _remove_invalid_records( db )

	# Delete foreign references
	for old_table in FOREIGN_TABLES:
		_fix_references( db, old_table, bad_values )

	# Delete from Resources table
	_delete_from_resources( db, bad_values )

def evolve(context):
	"""
	Evolve to generation 10
	"""
	do_evolve(context)
