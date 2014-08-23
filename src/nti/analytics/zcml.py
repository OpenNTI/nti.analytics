#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.component.zcml import utility

from nti.async.interfaces import IQueue
from nti.async.interfaces import IRedisQueue
from nti.async.redis_queue import RedisQueue
from nti.async import get_job_queue as async_queue

from nti.dataserver.interfaces import IRedisClient

from . import FAIL_QUEUE
from . import QUEUE_NAME
from . import QUEUE_NAMES

from .interfaces import IAnalyticsQueueFactory

class ImmediateQueueRunner(object):
	"""
	A queue that immediately runs the given job. This is generally
	desired for test or dev mode.
	"""
	def put(self, job):
		job()

@interface.implementer(IAnalyticsQueueFactory)
class _ImmediateQueueFactory(object):

	def get_queue( self, name ):
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
		queues = list(QUEUE_NAMES)
		queues.append(FAIL_QUEUE)
		queues.append(QUEUE_NAME)
		for name in queues:
			queue = RedisQueue(self._redis, name)
			utility(_context, provides=IRedisQueue, component=queue, name=name)

	def _redis(self):
		return component.getUtility(IRedisClient)

def registerImmediateProcessingQueue(_context):
	logger.info( "Registering immediate analytics processing queue" )
	factory = _ImmediateQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory)

def registerProcessingQueue(_context):
	logger.info( "Registering analytics processing queue" )
	factory = _AnalyticsProcessingQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory)

def registerRedisProcessingQueue(_context):
	logger.info( "Registering analytics redis processing queue" )
	factory = _AnalyticsRedisProcessingQueueFactory(_context)
	utility(_context, provides=IAnalyticsQueueFactory, component=factory)
