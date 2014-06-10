#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pyramid views.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson as json

from zope import interface
from zope.location.interfaces import IContained
from zope.container import contained as zcontained
from zope.traversing.interfaces import IPathAdapter

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.dataserver import users
from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict

from nti.ntiids import ntiids

from nti.utils.maps import CaseInsensitiveDict

@interface.implementer(IPathAdapter, IContained)
class AnalyticsPathAdapter(zcontained.Contained):

	__name__ = 'analyticsdb'

	def __init__(self, context, request):
		self.context = context
		self.request = request
		self.__parent__ = context

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest',
					  permission=nauth.ACT_READ,
					  context=AnalyticsPathAdapter,
					  request_method='GET')
_post_view_defaults = _view_defaults.copy()
_post_view_defaults['request_method'] = 'POST'

