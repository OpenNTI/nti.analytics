#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope.component.hooks import getSite
from zope.component.hooks import site, setHooks

from nti.analytics.database import get_analytics_db

from nti.site.hostpolicy import run_job_in_all_host_sites

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

def do_evolve( context, evolve_job, generation ):
	"""
	Run the given migration job in all host sites, if applicable.
	"""
	setHooks()

	db = get_analytics_db( strict=False )

	# Swap out ds_intids for ntiids
	ds_folder = context.connection.root()['nti.dataserver']

	def run_job():
		# Want to abort if our site doesnt havent db
		db = get_analytics_db( strict=False )

		if db is None:
			return
		else:
			site = getSite()
			logger.info( '[%s] Running analytics evolve (%s)',
						site.__name__, generation )
			evolve_job()

	with site( ds_folder ):
		if db is None:
			# Site specific dbs
			run_job_in_all_host_sites( partial( run_job ) )
		else:
			# Global db
			evolve_job()
