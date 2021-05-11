#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.component.zcml import utility

from nti.asynchronous.interfaces import IQueue
from nti.asynchronous.interfaces import IRedisQueue

from nti.asynchronous.redis_queue import RedisQueue

from nti.asynchronous.scheduled import ImmediateQueueRunner
from nti.asynchronous.scheduled import NonRaisingImmediateQueueRunner

from nti.asynchronous import get_job_queue as async_queue

from nti.dataserver.interfaces import IRedisClient

from . import QUEUE_NAMES

from .interfaces import IAnalyticsQueueFactory


@interface.implementer(IAnalyticsQueueFactory)
class _TestImmediateQueueFactory(object):
	"""
	Used for inlining jobs during tests. These tests may fail for various
	test ad-hoc reasons. This job runner will swallow such exceptions.

	This should not be used in any live environment.
	"""

	def get_queue(self, name):
		return NonRaisingImmediateQueueRunner()


@interface.implementer(IAnalyticsQueueFactory)
class _ImmediateQueueFactory(object):
	"""
	Used for inlining jobs in live environments.
	"""

	def get_queue(self, name):
		return ImmediateQueueRunner()


@interface.implementer(IAnalyticsQueueFactory)
class _AbstractProcessingQueueFactory(object):

	queue_interface = None

	def get_queue( self, name ):
		queue = async_queue(name, self.queue_interface)
		if queue is None:
			raise ValueError("No queue exists for analytics processing queue (%s). "
							 "Evolve error?" % name )
		return queue

class _AnalyticsProcessingQueueFactory(_AbstractProcessingQueueFactory):
	queue_interface = IQueue

class _AnalyticsRedisProcessingQueueFactory(_AbstractProcessingQueueFactory):
	queue_interface = IRedisQueue

	def __init__(self, _context):
		for name in QUEUE_NAMES:
			queue = RedisQueue(self._redis, name)
			utility(_context, provides=IRedisQueue, component=queue, name=name)

	def _redis(self):
		return component.getUtility(IRedisClient)

def registerImmediateProcessingQueue(_context):
	logger.info( "Registering immediate analytics processing queue" )
	factory = _ImmediateQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory)

def registerTestImmediateProcessingQueue(_context):
	logger.info( "Registering test immediate analytics processing queue" )
	factory = _TestImmediateQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory)

def registerProcessingQueue(_context):
	logger.info( "Registering analytics processing queue" )
	factory = _AnalyticsProcessingQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory)

def registerRedisProcessingQueue(_context):
	logger.info( "Registering analytics redis processing queue" )
	factory = _AnalyticsRedisProcessingQueueFactory(_context)
	utility(_context, provides=IAnalyticsQueueFactory, component=factory)
