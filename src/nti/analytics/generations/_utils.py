#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope import interface
from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site, setHooks

from nti.analytics.database import get_analytics_db

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import run_job_in_all_host_sites

@interface.implementer(IDataserver)
class MockDataserver(object):

	root = None

	def get_by_oid(self, oid, ignore_creator=False):
		resolver = component.queryUtility(IOIDResolver)
		if resolver is None:
			logger.warn("Using dataserver without a proper ISiteManager configuration.")
		else:
			return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
		return None

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

def do_evolve( context, evolve_job, generation, with_library=False ):
	"""
	Run the given migration job in all host sites, if applicable.
	"""
	setHooks()

	db = get_analytics_db( strict=False )

	# Swap out ds_intids for ntiids
	ds_folder = context.connection.root()['nti.dataserver']

	def run_job():
		# Want to abort if our site doesn't have a db.
		db = get_analytics_db( strict=False )

		if db is None:
			return
		else:
			site = getSite()
			logger.info( '[%s] Running analytics evolve (%s)',
						site.__name__, generation )
			evolve_job()

	if with_library:
		mock_ds = MockDataserver()
		mock_ds.root = ds_folder
		component.provideUtility(mock_ds, IDataserver)

	with site( ds_folder ):
		if with_library:
			# Load library
			library = component.queryUtility(IContentPackageLibrary)
			if library is not None:
				library.syncContentPackages()

			# If with library, we have to run by site, to
			# get the necessary courses per site.
			run_job_in_all_host_sites( partial( run_job ) )
		else:
			if db is None:
				# Site specific dbs
				run_job_in_all_host_sites( partial( run_job ) )
			else:
				# Global db
				evolve_job()
