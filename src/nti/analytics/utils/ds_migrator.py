#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import argparse
import time
import transaction
import sys

from zope import component

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.analytics.utils import all_objects_iids
from nti.analytics.interfaces import IObjectProcessor

class _AnalyticsMigrator(object):

	def __init__(self, usernames, last_oid, last_oid_file, batch_size):
		self.usernames = usernames
		self.last_oid = last_oid
		self.last_oid_file = last_oid_file
		self.batch_size = batch_size

	def init( self, obj ):
		result = False
		for _, module in component.getUtilitiesFor(IObjectProcessor):
			result = module.init( obj ) or result
		return result

	def init_db( self ):
		count = 0
		for ds_id, obj in all_objects_iids( self.usernames, self.last_oid ):
			if self.init( obj ):
				count += 1
				self.last_oid = ds_id
				if count % 10000 == 0:
					logger.info( 'Processed %s objects...', count)
					transaction.savepoint( optimistic=True )
			if self.batch_size and count > self.batch_size:
				break

		return count

	def _init_migration( self ):
		logger.info( 'Initializing analytics ds migrator (usernames=%s) (last_oid=%s) (batch_size=%s)',
					len( self.usernames ), self.last_oid, self.batch_size )
		now = time.time()
		total = 0

		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		while True:
			last_valid_id = self.last_oid
			try:
				count = transaction_runner( self.init_db, retries=2, sleep=1 )
				last_valid_id = self.last_oid
				logger.info( 'Committed batch (%s) (last_oid=%s)', count, last_valid_id )
				total += count
				if 		( self.batch_size and count <= self.batch_size ) \
					or 	self.batch_size is None:
					break
			finally:
				# Store our state
				with open( self.last_oid_file, 'w+' ) as f:
					f.write( str( last_valid_id ) )

		elapsed = time.time() - now
		logger.info("Total objects processed (size=%s) (time=%s)", total, elapsed)

def start_migration( args ):
	arg_parser = argparse.ArgumentParser(description="Create a user-type object")
	arg_parser.add_argument('--usernames', help="The usernames to migrate")
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('--batch_size', help="Commit after each batch")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	args = arg_parser.parse_args(args=args)

	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )

	last_oid_file = env_dir + '/.analytics_ds_migrator'
	last_oid = 0
	if os.path.exists( last_oid_file ):
		with open( last_oid_file, 'r' ) as f:
			file_last_oid = f.read()
			if file_last_oid:
				last_oid = int( file_last_oid )

	usernames = args.usernames
	if usernames:
		usernames = usernames.split(',')
	else:
		usernames = ()

	batch_size = 2000
	if args.batch_size:
		batch_size = args.batch_size

	conf_packages = ('nti.analytics','nti.appserver', 'nti.dataserver',)

	analytics_migrator = _AnalyticsMigrator( usernames, last_oid, last_oid_file, batch_size )

	run_with_dataserver(environment_dir=env_dir,
						 xmlconfig_packages=conf_packages,
						 verbose=args.verbose,
						 function=analytics_migrator._init_migration )


def main(args=None):
	start_migration(args)
	sys.exit(0)

if __name__ == '__main__':
	main()

