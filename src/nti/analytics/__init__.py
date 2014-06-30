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
def get_job_queue():
	return async_queue( QUEUE_NAME )


# Hmm, this won't work for locally added objects.  The objects are not committed 
# at the time we try to retrieve them.  A bit surprising since I would think
# they exist for this thread's session at least.
class _ImmediateQueueRunner(object):
	
	def put( self, job ):
		transaction_runner = \
				component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		try:
			# FIXME but this breaks mockDS tests
			#transaction_runner( job )
			
			job()
			
			# FIXME This doesn't work when running admin_view; ZTE issue?
			#job()
# 			
# 			  File "/Users/jzuech/Projects/buildout-eggs/SQLAlchemy-0.9.6-py2.7-macosx-10.9-intel.egg/sqlalchemy/orm/session.py", line 298, in _connection_for_bind
#     self._assert_active()
#   File "/Users/jzuech/Projects/buildout-eggs/SQLAlchemy-0.9.6-py2.7-macosx-10.9-intel.egg/sqlalchemy/orm/session.py", line 210, in _assert_active
#     % self._rollback_exception
# InvalidRequestError: This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback(). Original exception was: (IntegrityError) column user_ds_id is not unique u'INSERT INTO "Users" (user_ds_id) VALUES (?)' (97987269143875495,)
		except Exception as e:
			logger.exception( 'While migrating job (%s)', job )

def _get_job_queue():
	return _ImmediateQueueRunner()

get_job_queue = _get_job_queue