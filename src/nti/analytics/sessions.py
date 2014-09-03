# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from pyramid.threadlocal import get_current_request

from nti.socketio import interfaces as sio_interfaces

from datetime import datetime

from .common import get_entity
from .common import process_event

from nti.analytics.database import users as db_users

from nti.analytics import interfaces as analytic_interfaces

from nti.analytics import get_factory
from nti.analytics import SESSIONS_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )

def _add_session( user, nti_session, timestamp, ip_addr=None, platform=None, version=None ):
	if nti_session:
		user = get_entity( user )
		db_users.create_session( user, nti_session, timestamp, ip_addr, platform, version )
		logger.debug( 'Session created (user=%s)', user )

