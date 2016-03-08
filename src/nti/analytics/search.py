#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from pyramid.threadlocal import get_current_request

from zope import component

from nti.contentsearch.interfaces import ISearchCompletedEvent

from nti.analytics.common import process_event

from nti.analytics.database import search as db_search

from nti.analytics.sessions import get_nti_session_id

from nti.analytics import get_factory
from nti.analytics import SEARCH_ANALYTICS

get_search_queries = db_search.get_search_queries

def _get_search_queue():
	factory = get_factory()
	return factory.get_queue( SEARCH_ANALYTICS )

def _store_search( *args, **kwargs ):
	db_search.create_search_event( *args, **kwargs )

@component.adapter( ISearchCompletedEvent )
def _search_completed( event ):
	# Note: these search events are fired as the user types out
	# their (potentially long) search string. This may lead to
	# many similar event terms in succession.
	course_id = event.query.context.get( 'course' )
	nti_session = get_nti_session_id()
	process_event( 	_get_search_queue,
					_store_search,
					timestamp=datetime.utcnow(),
					session_id=nti_session,
					username=event.user.username,
					elapsed=event.elapsed,
					hit_count=event.metadata.TotalHitCount,
					term=event.query.term,
					search_types=event.query.searchOn,
					course_id=course_id )

	# Make sure we commit our job
	request = get_current_request()
	if request is not None:
		request.environ['nti.request_had_transaction_side_effects'] = True

