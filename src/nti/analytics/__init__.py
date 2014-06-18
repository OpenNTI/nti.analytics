#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
analytics module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import logging

from zope import component
from zc.blist import BList

from pyramid.threadlocal import get_current_request

from .database import interfaces as analytic_interfaces

from nti.async import create_job as create_job_async
from nti.async import get_job_queue as async_queue

QUEUE_NAME = 'nti.analytics'

def get_possible_site_names(request=None, include_default=True):
	request = request or get_current_request()
	if not request:
		return () if not include_default else ('',)
	__traceback_info__ = request

	site_names = getattr(request, 'possible_site_names', ())
	if include_default:
		site_names += ('',)
	return site_names

def get_analytics_db(names=None, request=None):
	names = names.split() if isinstance(names, six.string_types) else names
	names = names or get_possible_site_names(request=request)
	for site in names:
		db = component.queryUtility( analytic_interfaces.IAnalyticsDB, name=site )
		if db is not None:
			return db
	return None

def _execute_job( *args, **kwargs ):
	""" Execute our job, giving it a db and wrapping it with a session as we go. """
	effective_kwargs = dict( kwargs )
	site = effective_kwargs.pop( 'site', '' )
	
	# TODO raise if we don't have a database? Log and return?
	db = get_analytics_db( names=site )
	effective_kwargs['db'] = db
	args = BList( args )
	func = args.pop( 0 )
	
	func( *args, **effective_kwargs )

def create_job(func, *args, **kwargs):
	args = [func] + list(args)
	return create_job_async( _execute_job, *args, **kwargs )

def get_job_queue():
	return async_queue( QUEUE_NAME )

