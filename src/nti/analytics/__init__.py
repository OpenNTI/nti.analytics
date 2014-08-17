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

from nti.async import create_job as create_job_async

from nti.analytics.interfaces import IAnalyticsQueueFactory

QUEUE_NAME = '++etc++analytics++queue'

def _execute_job( *args, **kwargs ):
	""" Execute our job. """
	args = BList( args )
	func = args.pop( 0 )

	func( *args, **kwargs )

def create_job(func, *args, **kwargs):
	args = [func] + list(args)
	return create_job_async( _execute_job, *args, **kwargs )

def get_job_queue():
	factory = component.getUtility( IAnalyticsQueueFactory )
	return factory.get_queue()

