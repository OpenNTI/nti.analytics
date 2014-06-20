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

from nti.dataserver import interfaces as nti_interfaces

from .. import interfaces as analytic_interfaces

def all_objects_iids(users=()):
    
    obj = intids = component.getUtility(zope.intid.IIntIds)
    usernames = {getattr(user, 'username', user).lower() for user in users or ()}
    for uid in intids:
        try:
            obj = intids.getObject(uid)
            if nti_interfaces.IEntity.providedBy(obj):
                if not usernames or obj.username in usernames:
                    yield uid, obj
            else:
                creator = getattr(obj, 'creator', None)
                creator = getattr(creator, 'username', creator)
                creator = creator.lower() if creator else ''
                
                # TODO There are some objects without a creator, do we want to try to import those?	
                # - probably not, they wont' fit in our structure depending on what they are.
                # How about friends list?
                # TODO how about deleted items?  We probably want deleted items.
                # - probably not also	
                if    not nti_interfaces.IDeletedObjectPlaceholder.providedBy(obj) and \
                    (not usernames or creator in usernames):
                    yield uid, obj
        except (TypeError, POSKeyError) as e:
            logger.error("Error processing object %s(%s); %s", type(obj), uid, e)

