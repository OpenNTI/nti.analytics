#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import csv

from nti.analytics.database.resources import get_resource_record

resource_filename = __import__('pkg_resources').resource_filename

COLUMN_EXISTS_QUERY = 	"""
						SELECT *
						FROM information_schema.COLUMNS
						WHERE TABLE_SCHEMA = 'Analytics'
							AND TABLE_NAME = '%s'
							AND COLUMN_NAME = '%s'
						"""

def mysql_column_exists( con, table, column ):
	res = con.execute( COLUMN_EXISTS_QUERY % ( table, column ) )
	return res.scalar()

def store_video_duration_times( db, filename ):
	"""
	From a csv file in our `resources` folder, pulls ntiid -> max_time_length
	values to insert or update in our backing db.
	Returns a tuple of counts, missing_values.
	"""
	count = missing_count = 0
	file_path = resource_filename( __name__, 'resources/' + filename )
	# 'U' - universal newline mode (what, generated on windows?)
	with open( file_path, 'rU' ) as f:
		csv_reader = csv.reader( f )
		for row in csv_reader:
			if row:
				try:
					resource_ntiid = row[0]
					max_time_length = int( float( row[1] ) )
					get_resource_record( db, resource_ntiid, create=True,
										max_time_length=max_time_length )
					count += 1
				except ValueError:
					# No time data
					missing_count += 1
	return count, missing_count
