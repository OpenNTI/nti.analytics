#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.threadlocal import get_current_request

from nti.dataserver.users import User

from nti.contentsearch import interfaces as search_interfaces

from . import create_job
from . import get_graph_db
from . import get_job_queue
from . import relationships
from . import interfaces as graph_interfaces

def _create_search_relationship(db, username, query=None, properties=None):
	user = User.get_entity(username)
	if user and query:
		rel = db.create_relationship(user, query, relationships.Search(),
									 properties=properties)
		logger.debug("search relationship %s created", rel)
		return rel

def _process_search_event(db, event):
	request = get_current_request()
	if not request:
		return

	user = event.user
	results = event.results
	rel_type = relationships.Search()
	properties = component.queryMultiAdapter((user, results, rel_type),
											 graph_interfaces.IPropertyAdapter)
	if properties:
		queue = get_job_queue()
		job = create_job(_create_search_relationship, db=db, username=user.username,
						 query=event.query, properties=properties)
		queue.put(job)
		request.environ[b'nti.request_had_transaction_side_effects'] = b'True'

@component.adapter(search_interfaces.ISearchCompletedEvent)
def _search_completed(event):
	db = get_graph_db()
	if db is not None:
		_process_search_event(db, event)

component.moduleProvides(graph_interfaces.IObjectProcessor)

def init(db, obj):
	return False
