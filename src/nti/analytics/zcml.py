#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import schema
from zope import interface
from zope.component.zcml import utility

from nti.async.interfaces import IQueue
from nti.async import get_job_queue as async_queue

from nti.analytics import QUEUE_NAME
from nti.analytics.interfaces import IAnalyticsQueue
from nti.analytics.tests import ImmediateQueueRunner

class IRegisterAnalyticsQueue(interface.Interface):
	"""
	The arguments needed for registering the analytics queue.
	"""

def registerImmediateProcessingQueue(_context):
	logger.info( "Registering immediate analytics processing queue" )
	queue = ImmediateQueueRunner()
	interface.alsoProvides(queue, IAnalyticsQueue)
	utility(_context, provides=IAnalyticsQueue, component=queue )

def registerProcessingQueue(_context):
	logger.info( "Registering analytics processing queue" )
	queue = async_queue( QUEUE_NAME )
	interface.alsoProvides(queue, IAnalyticsQueue)
	utility(_context, provides=IAnalyticsQueue, component=queue )
