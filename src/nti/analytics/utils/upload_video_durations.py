#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import csv
import sys
import argparse

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.analytics.database.resources import get_analytics_db
from nti.analytics.database.resources import get_resource_record

def _store_video_duration_times( db, filename ):
	"""
	From a given csv file, pulls ntiid -> max_time_length
	values to insert or update in our backing db.
	Returns a tuple of counts, missing_values.
	"""
	count = missing_count = 0
	# 'U' - universal newline mode (what, generated on windows?)
	with open( filename, 'rU' ) as f:
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

def _process_args(args):
	if args.site:
		set_site( args.site )
	db = get_analytics_db()
	count, missing_count = _store_video_duration_times( db, args.filename )
	logger.info( 'Finished uploading file (possible uploads=%s) (missing=%s)',
				count, missing_count )

def main():
	arg_parser = argparse.ArgumentParser(description="Upload analytic video duration times.")
	arg_parser.add_argument('-v', '--verbose', help="Be Verbose", action='store_true',
							dest='verbose')

	arg_parser.add_argument('-s', '--site',
							dest='site',
							help="Application SITE.")

	arg_parser.add_argument('-f', '--filename',
							 dest='filename',
							 help="CSV data input file.")

	args = arg_parser.parse_args()
	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")

	conf_packages = ('nti.appserver',)
	context = create_context(env_dir, with_library=False)

	run_with_dataserver(environment_dir=env_dir,
						verbose=args.verbose,
						xmlconfig_packages=conf_packages,
						context=context,
						minimal_ds=True,
						function=lambda: _process_args(args))
	sys.exit(0)

if __name__ == '__main__':
	main()
