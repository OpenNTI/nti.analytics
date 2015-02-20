#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
import transaction
from functools import partial

from zope import component

from nti.dataserver.interfaces import IDataserverTransactionRunner

from ..recorded.interfaces import IObjectViewedRecordedEvent

from .utils import create_user_event

from . import get_current_username

from . import VIEW_API

def _process_view(username, oid, params=None):
	return create_user_event(event=VIEW_API, 
			  		 	 	 user=username,
			  		 	 	 obj=oid,
			  			 	 params=params)

def _process_view_event(username, oid):

	def _process_event():
		transaction_runner = component.getUtility(IDataserverTransactionRunner)
		func = partial(_process_view, username=username, oid=oid)
		transaction_runner(func)

	transaction.get().addAfterCommitHook(
						lambda success: success and gevent.spawn(_process_event))

@component.adapter(IObjectViewedRecordedEvent)
def _object_viewed(event):
	username = get_current_username()
	if username:
		pass
