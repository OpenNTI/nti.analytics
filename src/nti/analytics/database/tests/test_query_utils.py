#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from hamcrest import assert_that
from hamcrest import has_entries

from sqlalchemy.orm.query import Query

from nti.analytics.database.database import AnalyticsDB

from nti.analytics.database.interfaces import IAnalyticsDB

from nti.analytics.database.query_utils import _do_context_and_timestamp_filtering

from nti.analytics.database.sessions import Sessions

from nti.analytics.tests import AnalyticsTestBase


class TestQueryUtils(AnalyticsTestBase):

    def setUp(self):
        # Want to start with a fresh db here
        super(TestQueryUtils, self).setUp()
        self.db = AnalyticsDB( dburi='sqlite://', testmode=True )
        component.getGlobalSiteManager().registerUtility( self.db, IAnalyticsDB )
        self.session = self.db.session

    def tearDown(self):
        super(TestQueryUtils, self).tearDown()
        component.getGlobalSiteManager().unregisterUtility( self.db )
        self.session.close()

    def test_query_utils_return_list_by_default(self):
        results = _do_context_and_timestamp_filtering(Sessions)
        assert_that(isinstance(results, list), True)

    def test_query_utils_returns_iterable_query(self):
        results = _do_context_and_timestamp_filtering(Sessions, yield_per=None)
        assert_that(isinstance(results, Query), True)

    def test_query_utils_return_yielding_query(self):
        results = _do_context_and_timestamp_filtering(Sessions, yield_per=10)
        assert_that(isinstance(results, Query), True)
        assert_that(results.__dict__['_execution_options'],
                        has_entries('stream_results', True,
                                    'max_row_buffer', 10))

