#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import predictionio

from zope import component

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageLibrary

from . import get_user
from . import get_predictionio_app

from .interfaces import ITypes
from .interfaces import IProperties

def get_content_unit(unit):
	if not IContentUnit.providedBy(unit):
		library = component.queryUtility(IContentPackageLibrary)
		paths = library.pathToNTIID(str(unit)) if library else ()
		result = paths[-1] if paths else None
	else:
		result = unit
	return result

def record_content_view(user, unit, params=None, request=None):
	user = get_user(user)
	unit = get_content_unit(unit)
	app = get_predictionio_app()
	if app is not None and unit is not None and user is not None:
		ntiid = unit.ntiid
		params = params or {}
		client = predictionio.Client(app.AppKey, apiurl=app.URL)
		try:
			client.create_user(user.username, params=IProperties(user))
			client.create_item(ntiid, ITypes(unit), IProperties(unit))
			client.identify(user.username)
			client.record_action_on_item("view", ntiid, params=params)
		finally:
			client.close()
		logger.debug("item '%s' was viewed by %s", ntiid, user)
