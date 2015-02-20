#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from .interfaces import IOID
from .interfaces import IType
from .interfaces import IProperties

from . import get_user
from . import object_finder
from . import get_predictionio_client

def create_user_event(event, user, obj, params=None, client=None):
	result = False
	should_close = (client is None)
	client = get_predictionio_client(client=client)
	if client is None:
		return result
	try:
		params = params or {}
		user = get_user(user)
		obj = object_finder(obj)
		if obj is not None and user is not None:
			oid = IOID(obj)
			
			client.create_event(event="$set",
  								entity_type="user",
  								entity_id=IOID(user),
  								properties=IProperties(user))
			
			client.create_event(event="$set",
  								entity_type=IType(obj),
    							entity_id=oid,
    							properties=IProperties(obj))
			
			client.create_event(event=event,
  								entity_type="user",
    							entity_id=IOID(user),
								target_entity_type=IType(obj),
								target_entity_id=oid,
								properties=params)
			result = True
			logger.debug("%s recorded event %s for %s", user, event, oid)
	finally:
		if should_close:
			client.close()
	return result
