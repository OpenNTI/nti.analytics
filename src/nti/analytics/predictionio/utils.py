#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import pytz
import isodate
import numbers
from datetime import datetime

from geoip import geolite2

from nti.analytics.identifier import SessionId
from nti.analytics.database.sessions import get_session_by_id

from .interfaces import IOID
from .interfaces import IType
from .interfaces import IProperties

from . import get_user
from . import object_finder
from . import get_predictionio_client

def get_lat_lang(nti_session=None):
	sid = SessionId.get_id(nti_session)
	session = get_session_by_id(sid) if sid else None
	ip_addr = getattr(session, 'ip_addr', None)
	match = geolite2.lookup( ip_addr ) if ip_addr else None
	if match is not None:
		result = match.location or ()
		return result
	return None

def parse_event_time(event_time=None):
	try:
		if isinstance(event_time, numbers.Number):
			event_time = datetime.fromtimestamp(event_time, pytz.utc)
		elif isinstance(event_time, six.string_types):
			event_time = isodate.parse_datetime(event_time)
	except (ValueError, TypeError):
		event_time = None
	return event_time

def create_user_event(event, user, obj, params=None, event_time=None, client=None):
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
								properties=params,
								event_time=parse_event_time(event_time))
			result = True
			logger.debug("%s recorded event %s for %s", user, event, oid)
	finally:
		if should_close:
			client.close()
	return result
