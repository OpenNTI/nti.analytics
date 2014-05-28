#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import transaction
import simplejson as json

from zope import component

from pyramid.view import view_config

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.interfaces import LocatedExternalDict

from nti.utils.maps import CaseInsensitiveDict

from . import utils
from . import views
from . import get_job_queue
from . import interfaces as graph_interfaces

def _make_min_max_btree_range(search_term):
	min_inclusive = search_term # start here
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive

def username_search(search_term):
	min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
	dataserver = component.getUtility(nti_interfaces.IDataserver)
	_users = nti_interfaces.IShardLayout(dataserver).users_folder
	usernames = list(_users.iterkeys(min_inclusive, max_exclusive, excludemax=True))
	return usernames

def init(db, obj):
	result = False
	for _, module in component.getUtilitiesFor(graph_interfaces.IObjectProcessor):
		result = module.init(db, obj) or result
	return result

def init_db(db, usernames=()):
	count = 0
	for _, obj in utils.all_objects_iids(usernames):
		if init(db, obj):
			count += 1
			if count % 10000 == 0:
				transaction.savepoint()
	return count

@view_config(route_name='objects.generic.traversal',
			 name='init_graphdb',
			 renderer='rest',
			 request_method='POST',
			 context=views.GraphPathAdapter,
			 permission=nauth.ACT_MODERATE)
def init_graphdb(request):
	values = json.loads(unicode(request.body, request.charset)) if request.body else {}
	values = CaseInsensitiveDict(values)
	site = values.get('site', u'')
	term = values.get('term', values.get('search', None))
	usernames = values.get('usernames', values.get('username', None))
	if term:
		usernames = username_search(term)
	elif usernames:
		usernames = usernames.split(',')
	else:
		usernames = ()
	db = component.getUtility(graph_interfaces.IGraphDB, name=site)

	now = time.time()
	total = init_db(db, usernames)
	elapsed = time.time() - now

	logger.info("Total objects processed %s(%s)", total, elapsed)

	result = LocatedExternalDict()
	result['Elapsed'] = elapsed
	result['Total'] = total
	return result

@view_config(route_name='objects.generic.traversal',
			 name='queue_info',
			 renderer='rest',
			 request_method='GET',
			 context=views.GraphPathAdapter,
			 permission=nauth.ACT_MODERATE)
def queue_info(request):
	queue = get_job_queue()
	result = LocatedExternalDict()
	result['size'] = len(queue)
	return result

@view_config(route_name='objects.generic.traversal',
			 name='empty_queue',
			 renderer='rest',
			 request_method='POST',
			 context=views.GraphPathAdapter,
			 permission=nauth.ACT_MODERATE)
def empty_queue(request):
	queue = get_job_queue()
	now = time.time()
	done = queue.empty()
	result = LocatedExternalDict()
	result['Elapsed'] = time.time() - now
	result['Total'] = done
	return result
