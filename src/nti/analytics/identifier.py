#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from six import string_types

from zope import component
from zope import interface

from zope.intid import IIntIds

from ZODB.interfaces import IBroken

from ZODB.POSException import POSError

from nti.analytics_database.interfaces import IAnalyticsNTIIDFinder
from nti.analytics_database.interfaces import IAnalyticsIntidIdentifier
from nti.analytics_database.interfaces import IAnalyticsNTIIDIdentifier
from nti.analytics_database.interfaces import IAnalyticsRootContextIdentifier

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IAnalyticsIntidIdentifier)
class _DSIdentifier(object):

    def _get_intid_utility(self):
        intids = component.getUtility(IIntIds)
        return intids

    def get_id(self, obj):
        result = getattr(obj, '_ds_intid', None)
        return result or self._get_intid_utility().getId(obj)

    def get_object(self, uid):
        result = None
        try:
            obj = self._get_intid_utility().queryObject(uid, default=None)
            if not IBroken.providedBy(obj):
                result = obj
        except (TypeError, POSError):
            logger.warn('Broken object missing (id=%s)', uid)
        return result


@interface.implementer(IAnalyticsNTIIDIdentifier)
class _NTIIDIdentifier(object):

    def get_id(self, resource):
        """ 
        Resource could be a video or content piece. 
        """
        if isinstance(resource, string_types):
            result = resource
        else:
            result = getattr(resource, 'ntiid', None) \
                  or to_external_ntiid_oid(resource)

        return result

    def get_object(self, uid):
        return find_object_with_ntiid(uid)


@interface.implementer(IAnalyticsRootContextIdentifier)
class _RootContextIdentifier(object):

    def get_id(self, root_context):
        """ 
        Could be a course or content-package.
        """
        # TODO: It seems external OID would be preferrable,
        # perhaps much faster lookups.
        catalog_entry = ICourseCatalogEntry(root_context, None)
        result = getattr(catalog_entry, 'ntiid', None)

        if result is None:
            # Legacy course or content
            result = getattr(root_context, 'ContentPackageNTIID',
                             getattr(root_context, 'ntiid', None))
        return result

    def get_object(self, ntiid):
        obj = find_object_with_ntiid(ntiid)
        # We may have:
        # 1. content package -> legacy course
        # 2. catalog entry -> new course
        # 3. content package / book
        # Adapt for 1,2; return 3.
        obj = ICourseInstance(obj, obj)
        return obj


@interface.implementer(IAnalyticsNTIIDFinder)
class _AnalyticsNTIIDFinder(object):

    __slots__ = ()

    def find(self, ntiid):
        return find_object_with_ntiid(ntiid)


def get_ds_object(obj_id):
    id_utility = component.getUtility(IAnalyticsIntidIdentifier)
    return id_utility.get_object(obj_id)


def get_ntiid_object(obj_id):
    id_utility = component.getUtility(IAnalyticsNTIIDIdentifier)
    return id_utility.get_object(obj_id)


def get_root_context_object(obj_id):
    id_utility = component.getUtility(IAnalyticsRootContextIdentifier)
    return id_utility.get_object(obj_id)


def get_ds_id(obj):
    id_utility = component.getUtility(IAnalyticsIntidIdentifier)
    return id_utility.get_id(obj)


def get_ntiid_id(obj):
    id_utility = component.getUtility(IAnalyticsNTIIDIdentifier)
    return id_utility.get_id(obj)


def get_root_context_id(obj):
    id_utility = component.getUtility(IAnalyticsRootContextIdentifier)
    return id_utility.get_id(obj)
