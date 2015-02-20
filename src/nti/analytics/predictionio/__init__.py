#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.security.management import queryInteraction

from predictionio import EventClient

from nti.dataserver.users import User
from nti.dataserver.interfaces import IUser

from nti.ntiids.ntiids import find_object_with_ntiid

from .interfaces import IPredictionIOApp

VIEW_API = "view"

def get_predictionio_app(name=''):
	result = component.getUtility(IPredictionIOApp, name=name)
	return result

def get_current_username():
	interaction = queryInteraction()
	participations = list(getattr(interaction, 'participations', None) or ())
	participation = participations[0] if participations else None
	principal = getattr(participation, 'principal', None)
	result = principal.id if principal is not None else None
	return result

def get_user(user=None):
	user = get_current_username() if user is None else user
	if user is not None and not IUser.providedBy(user):
		user = User.get_user(str(user))
	return user
get_current_user = get_user

def get_predictionio_client(client=None, name=''):
	if client is None:
		app = get_predictionio_app(name=name)
		client = EventClient(app.AppKey, apiurl=app.URL) if app is not None else None
	return client

def find_object(oid):
	return find_object_with_ntiid(oid) if oid else None
object_finder = find_object
