#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.externalization.interfaces import IInternalObjectExternalizer
from nti.externalization.interfaces import StandardExternalFields

from nti.analytics_database.meta_mixins import BaseViewMixin

from .users import get_user

VIEW_EVENT_SUMMARY_MIMETYPE = 'application/vnd.nextthought.analytics.vieweventsummary'

@interface.implementer(IInternalObjectExternalizer)
@component.adapter(BaseViewMixin)
class ViewEventSummaryExternalizer(object):

    def __init__(self, event=None):
        self.event = event

    def toExternalObject(self, **kwargs):
        ext = {}
        ext['SessionID'] = self.event.SessionID
        ext['Timestamp'] = self.event.timestamp
        ext['Username'] = getattr(get_user(self.event.user_id), 'username', None)
        ext[StandardExternalFields.MIMETYPE] = VIEW_EVENT_SUMMARY_MIMETYPE
        return ext
