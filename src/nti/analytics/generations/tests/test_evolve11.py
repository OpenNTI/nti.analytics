#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 6.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from hamcrest import assert_that
from hamcrest import has_length

from nti.analytics.generations.evolve11 import _delete_zero_length_records

from nti.analytics.database import get_analytics_db
from nti.analytics.database.enrollments import CourseCatalogViews
from nti.analytics.database.users import Users
from nti.analytics.database.root_context import Courses

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.tests import NTIAnalyticsTestCase

class TestEvolve11(NTIAnalyticsTestCase):

	@WithMockDSTrans
	def test_evolve11(self):
		# Populate with relevant data
		with mock_dataserver.mock_db_trans(self.ds):
			db = get_analytics_db()

			user = Users( 	user_ds_id=1,
						allow_research=False,
						username='robert',
						username2='paulson' )

			course = Courses(
							context_id=1,
							context_ds_id=1,
							context_name='hard',
							context_long_name='knocks' )

			db.session.add( user )
			db.session.add( course )

			for _ in range( 5 ):
				view_event = CourseCatalogViews(
										user_id=1,
										session_id=1,
										timestamp=datetime.now(),
										course_id=1,
										time_length=0 )

				db.session.add( view_event )

			for _ in range( 5 ):
				view_event = CourseCatalogViews(
										user_id=1,
										session_id=1,
										timestamp=datetime.now(),
										course_id=1,
										time_length=100 )

				db.session.add( view_event )

		db = get_analytics_db()
		all_resources = db.session.query( CourseCatalogViews ).all()
		assert_that( all_resources, has_length( 10 ))

		# Do it
		with mock_dataserver.mock_db_trans(self.ds):
			db = get_analytics_db()
			_delete_zero_length_records( db, CourseCatalogViews )

		db = get_analytics_db()
		all_resources = db.session.query( CourseCatalogViews ).all()
		assert_that( all_resources, has_length( 5 ))
