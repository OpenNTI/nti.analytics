#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid

from zope import component
from zope import interface

from ZODB.POSException import POSKeyError

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

def all_objects_iids(users, last_oid):
	obj = intids = component.getUtility(zope.intid.IIntIds)
	usernames = {getattr(user, 'username', user).lower() for user in users or ()}

	# These should be in order.
	valid_intids = (x for x in intids if x > last_oid )
	for uid in valid_intids:
		try:
			obj = intids.getObject(uid)
			if IEntity.providedBy(obj):
				if not usernames or obj.username in usernames:
					yield uid, obj
			else:
				creator = getattr(obj, 'creator', None)
				creator = getattr(creator, 'username', creator)
				try:
					creator = creator.lower() if creator else ''
				except AttributeError:
					pass
				if	not IDeletedObjectPlaceholder.providedBy(obj) and \
					(not usernames or creator in usernames):
					yield uid, obj
		except (TypeError, POSKeyError) as e:
			logger.error("Error processing object %s(%s); %s", type(obj), uid, e)
