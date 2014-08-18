#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Directives to be used in ZCML

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.component.zcml import utility

from nti.async import get_job_queue as async_queue

from nti.analytics.interfaces import IAnalyticsQueueFactory

class ImmediateQueueRunner(object):
	"""
	A queue that immediately runs the given job. This is generally
	desired for test or dev mode.
	"""
	def put( self, job ):
		job()

@interface.implementer(IAnalyticsQueueFactory)
class _ImmediateQueueFactory(object):

	def get_queue( self, name ):
		return ImmediateQueueRunner()

@interface.implementer(IAnalyticsQueueFactory)
class _AnalyticsProcessingQueueFactory(object):

	def get_queue( self, name ):
		queue = async_queue( name )
		if queue is None:
			raise ValueError( "No queue exists for analytics processing queue (%s). Evolve error?" % name )
		return queue

def registerImmediateProcessingQueue(_context):
	logger.info( "Registering immediate analytics processing queue" )
	factory = _ImmediateQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory )

def registerProcessingQueue(_context):
	logger.info( "Registering analytics processing queue" )
	factory = _AnalyticsProcessingQueueFactory()
	utility( _context, provides=IAnalyticsQueueFactory, component=factory )
