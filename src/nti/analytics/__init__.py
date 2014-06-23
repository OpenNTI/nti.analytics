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

def get_analytics_db():
	return component.getUtility( analytic_interfaces.IAnalyticsDB )

def _execute_job( *args, **kwargs ):
	""" Execute our job, giving it a db and wrapping it with a session as we go. """
	db = get_analytics_db()
	
	effective_kwargs = dict( kwargs )
	effective_kwargs['db'] = db
	args = BList( args )
	func = args.pop( 0 )
	
	func( *args, **effective_kwargs )

def create_job(func, *args, **kwargs):
	args = [func] + list(args)
	return create_job_async( _execute_job, *args, **kwargs )
# 
# FIXME
# Can we toggle this based on dev/test mode?
# If so, we need to handle transactions/errors here.
# def get_job_queue():
# 	return async_queue( QUEUE_NAME )


class _ImmediateQueueRunner(object):
	
	def put( self, job ):
		transaction_runner = \
				component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		try:
			transaction_runner( job )
		except Exception as e:
			logger.error( 'While migrating job (%s)', job, e )

def _get_job_queue():
	return _ImmediateQueueRunner()

get_job_queue = _get_job_queue