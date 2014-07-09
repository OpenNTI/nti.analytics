#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
analytics module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import logging

from zope import component
from zc.blist import BList

from nti.dataserver import interfaces as nti_interfaces
from .database import interfaces as analytic_interfaces

from nti.async import create_job as create_job_async
from nti.async import get_job_queue as async_queue

QUEUE_NAME = '++etc++analytics++queue'
DEV_QUEUE_NAME = QUEUE_NAME + '++devmode'

def get_analytics_db():
	return component.getUtility( analytic_interfaces.IAnalyticsDB )

def _execute_job( *args, **kwargs ):
	""" Execute our job, pass it a kwarg analytics db. """
	db = get_analytics_db()
	
	__traceback_info__ = db.session
	
	effective_kwargs = dict( kwargs )
	effective_kwargs['db'] = db
	args = BList( args )
	func = args.pop( 0 )
	
	func( *args, **effective_kwargs )

def create_job(func, *args, **kwargs):
	args = [func] + list(args)
	return create_job_async( _execute_job, *args, **kwargs )

def get_job_queue():
	return async_queue( QUEUE_NAME )


# # Hmm, this won't work for locally added objects.  The objects are not committed 
# # at the time we try to retrieve them.  A bit surprising since I would think
# # they exist for this thread's session at least.
# class _ImmediateQueueRunner(object):
# 	
# 	def put( self, job ):
# # 		transaction_runner = \
# #  				component.getUtility(nti_interfaces.IDataserverTransactionRunner)
# 		try:
# 			# For top level processes (admin_views) we would need to run in a transaction_runner.
# 			#transaction_runner( job )
# 			
# 			# Any need to handle sessions here (outside of ZTE).
# 			job()
# 		except Exception as e:
# 			logger.exception( 'While migrating job (%s)', job )
# 
# def _get_job_queue():
# 	return _ImmediateQueueRunner()
# 
# get_job_queue = _get_job_queue