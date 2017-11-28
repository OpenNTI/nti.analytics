#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.dataserver.interfaces import IDataserverClosedEvent

from nti.analytics_database.database import AnalyticsDB

from nti.analytics_database.interfaces import IAnalyticsDB

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.analytics_database.zcml",
    "nti.analytics_database.zcml",
    "IRegisterAnalyticsDB",
    "registerAnalyticsDB",
)


@component.adapter(IDataserverClosedEvent)
def _closed_dataserver(unused_event):
    # This dupes what we have in config.zcml.
    logger.info('Resetting AnalyticsDB')
    db = AnalyticsDB(dburi='sqlite://', testmode=True, defaultSQLite=True)
    component.getSiteManager().registerUtility(db, IAnalyticsDB)
