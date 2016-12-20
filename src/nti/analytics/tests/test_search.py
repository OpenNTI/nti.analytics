#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import contains
from hamcrest import has_length
from hamcrest import assert_that

from zope.event import notify

from nti.analytics.search import get_search_queries

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import SearchCompletedEvent

from nti.contentsearch.search_results import SearchResults

from nti.dataserver.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.analytics.tests import NTIAnalyticsTestCase

class TestSearch( NTIAnalyticsTestCase ):

	@WithMockDSTrans
	def test_search(self):
		oz = User.create_user( username='Ozymandius' )
		gus = User.create_user( username='Augustus' )
		# Basic search without filters
		query = ISearchQuery("test")
		results = SearchResults(Query=query)
		elapsed_time = 5 #s
		event = SearchCompletedEvent( oz, results, elapsed_time )
		notify( event )

		queries = get_search_queries()
		result = queries[0]
		first_query_timestamp = result.timestamp
		assert_that( result.query_elapsed_time, is_( elapsed_time ))
		assert_that( result.RootContext, none())
		assert_that( result.user.username, is_( oz.username ) )
		assert_that( first_query_timestamp, not_none())
		assert_that( result.SearchTypes, none())
		assert_that( result.term, is_( 'test' ))
		assert_that( result.hit_count, is_( 0 ))

		# Search by type, with Gus
		query = ISearchQuery("empty")
		query.searchOn = ('videotranscript',)
		results = SearchResults(Query=query)
		elapsed_time = 30 #s
		event = SearchCompletedEvent( gus, results, elapsed_time )
		notify( event )

		queries = get_search_queries()
		assert_that( queries, has_length( 2 ))

		queries = get_search_queries( user=gus )
		assert_that( queries, has_length( 1 ))
		result = queries[0]
		assert_that( result.query_elapsed_time, is_( elapsed_time ))
		assert_that( result.RootContext, none())
		assert_that( result.user.username, is_( gus.username ) )
		assert_that( result.timestamp, not_none())
		assert_that( result.SearchTypes, contains( 'videotranscript' ))
		assert_that( result.term, is_( 'empty' ))
		assert_that( result.hit_count, is_( 0 ))

