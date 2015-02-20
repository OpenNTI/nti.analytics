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

from zope import component

from nti.dataserver.interfaces import IUser
from nti.dataserver.users.interfaces import IWillDeleteEntityEvent

from .interfaces import IOID

from . import get_predictionio_client

def _remove_user(userid):
	client = get_predictionio_client()
	if client is not None:
		try:
			client.delete_user(userid)
		finally:
			client.close()
		logger.debug("User '%s' was removed", userid)

def _process_removal(user):
	userid = IOID(user)
	def _process_event():
		_remove_user(userid=userid)
	transaction.get().addAfterCommitHook(
					lambda success: success and gevent.spawn(_process_event))

@component.adapter(IUser, IWillDeleteEntityEvent)
def _user_removed(user, event):
	_process_removal(user)
