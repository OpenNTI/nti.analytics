#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageLibrary

from . import get_user
from . import get_predictionio_client

from .interfaces import IOID
from .interfaces import IType
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
	if unit is not None and user is not None:
		client = get_predictionio_client()
		if client is None:
			return
		oid = IOID(unit)
		params = params or {}
		try:
			client.create_event(event="$set",
  								entity_type="user",
  								entity_id=user.username,
  								properties=IProperties(user))
			
			client.create_event(event="$set",
  								entity_type=IType(unit),
    							entity_id=oid,
    							properties=IProperties(unit))
			
			client.create_event(event="view",
  								entity_type="user",
    							entity_id=user.username,
								target_entity_type=IType(unit),
								target_entity_id=oid,
								properties=params)
		finally:
			client.close()
		logger.debug("item '%s' was viewed by %s", oid, user)
