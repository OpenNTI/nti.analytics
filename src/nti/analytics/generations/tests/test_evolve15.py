#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from hamcrest import assert_that
from hamcrest import has_item
from hamcrest import is_not

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Interval

from sqlalchemy.schema import Sequence
from sqlalchemy.engine.reflection import Inspector

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.generations.evolve15 import do_evolve
from nti.analytics.generations.evolve15 import _get_column_names

from nti.analytics.database import get_analytics_db

from nti.analytics.tests import NTIAnalyticsTestCase

class TestEvolve15(NTIAnalyticsTestCase):

	def _prep(self, db):
		connection = db.engine.connect()
		mc = MigrationContext.configure( connection )
		op = Operations(mc)

		op.drop_table( 'Courses' )

		# RootContext will be auto-created; add our previous Courses table.
		op.create_table(
				'Courses',
				Column('course_id', Integer, Sequence('course_id_seq'), index=True, nullable=False, primary_key=True ),
				Column('course_ds_id', Integer, nullable=True, index=True ),
				Column('course_name', String(64), nullable=True, unique=False, index=True),
				Column('course_long_name', String(128), nullable=True),
				Column('start_date', DateTime, nullable=True),
				Column('end_date', DateTime, nullable=True),
				Column('duration', Interval, nullable=True),
				Column('is_course', Boolean, default=True ) )

	@WithMockDSTrans
	def test_evolve15(self):
		db = get_analytics_db()
		self._prep( db )

		do_evolve()

		inspector = Inspector.from_engine( db.engine )

		# Verify table rename
		table_names = inspector.get_table_names()

		assert_that( table_names, has_item( 'Books' ) )
		assert_that( table_names, has_item( 'Courses' ) )

		# Verify column renames
		column_names = _get_column_names( inspector.get_columns( 'Courses' ) )

		assert_that( column_names, has_item( 'context_id' ) )
		assert_that( column_names, is_not( has_item( 'course_id' ) ) )

		assert_that( column_names, has_item( 'context_ds_id' ) )
		assert_that( column_names, is_not( has_item( 'course_ds_id' ) ) )

		assert_that( column_names, has_item( 'context_name' ) )
		assert_that( column_names, is_not( has_item( 'course_name' ) ) )

		assert_that( column_names, has_item( 'context_long_name' ) )
		assert_that( column_names, is_not( has_item( 'course_long_name' ) ) )

		# Verify indexes
		indexes = inspector.get_indexes( 'Courses' )
		index_names = [x['name'] for x in indexes]
		assert_that( index_names, has_item( 'ix_Courses_context_id' ))
		assert_that( index_names, has_item( 'ix_Courses_context_ds_id' ))
		assert_that( index_names, has_item( 'ix_Courses_context_name' ))

		# Re-migrate does not fail
		db = get_analytics_db()
		do_evolve()
