#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 6.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.generations.evolve8 import _remove_invalid_records

from nti.analytics.database import get_analytics_db
from nti.analytics.database.resources import Resources

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.tests import NTIAnalyticsTestCase

class TestEvolve8(NTIAnalyticsTestCase):

	@WithMockDSTrans
	def test_evolve8(self):
		# Populate with relevant data
		with mock_dataserver.mock_db_trans(self.ds):
			db = get_analytics_db()
			for i in range( 5 ):
				new_resource = Resources(
								resource_ds_id=str( i ),
								resource_display_name='bleh')

				db.session.add( new_resource )
			for i in [ 'a', 'b', 'c', 'd', 'e']:
				new_resource = Resources(
								resource_ds_id=i,
								resource_display_name='blah')

				db.session.add( new_resource )

		db = get_analytics_db()
		all_resources = db.session.query( Resources ).all()
		assert_that( all_resources, has_length( 10 ))

		# Do it
		with mock_dataserver.mock_db_trans(self.ds):
			db = get_analytics_db()
			_remove_invalid_records( db )

		db = get_analytics_db()
		all_resources = db.session.query( Resources ).all()
		assert_that( all_resources, has_length( 5 ))
