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

