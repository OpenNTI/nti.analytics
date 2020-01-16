#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.monkey import patch_sqlalchemy_on_import
patch_sqlalchemy_on_import.patch()

import argparse

from nti.analytics_database.database import AnalyticsDB


class DatabaseMigrator(object):
	"""
	Migrate data from one source analytics database to another. The
	destination database should exist but be empty to ensure a clean
	migration. The system of the target database should not be running
	during this migration.
	"""

	def create_arg_parser(self):
		arg_parser = argparse.ArgumentParser(description="Migrate analytics data between databases")
		arg_parser.add_argument('-s', '--source_db', dest='source_db',
								help="The source database url")
		arg_parser.add_argument('-t', '--target_db', dest='target_db',
							    help="The target database url")
		arg_parser.add_argument('-v', '--verbose', help="Be verbose",
								action='store_true', dest='verbose')
		return arg_parser

	def __call__(self, *args, **kwargs):
		arg_parser = self.create_arg_parser()
		args = arg_parser.parse_args()

		source_db = args.source_db
		if not source_db:
			raise ValueError("Must have source database url")

		target_db = args.target_db
		if not target_db:
			raise ValueError("Must have target database url")

		source = AnalyticsDB(source_db)
		target = AnalyticsDB(target_db)

		print('Migrating analytics databases (%s) (%s)' % (source_db, target_db))
		try:
			# Disable foreign key constraints
			if 'mysql' in target.dburi:
				target.engine.execute('SET FOREIGN_KEY_CHECKS=0')
			for table_name, table in source.metadata.metadata.tables.items():
				data = source.session.execute(table.select()).fetchall()
				print("Migrating table (%s) (%s)" % (table_name, len(data)))
				if data:
					target.engine.execute(table.insert(), data)
		except:
			raise
		print('Migration complete')

def main():
	return DatabaseMigrator()()


if __name__ == '__main__':
	main()
