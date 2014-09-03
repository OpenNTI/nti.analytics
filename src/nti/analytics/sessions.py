# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from pyramid.threadlocal import get_current_request

from nti.socketio import interfaces as sio_interfaces

from datetime import datetime

from .common import get_entity
from .common import process_event

from nti.appserver.interfaces import IUserLogonEvent
from nti.dataserver.interfaces import IUser

from nti.analytics.database import sessions as db_sessions

from nti.analytics import get_factory
from nti.analytics import SESSIONS_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )

def _add_session( username, platform, timestamp, ip_addr ):
	if username:
		user = get_entity( username )
		db_sessions.create_session( user, platform, timestamp, ip_addr )
		logger.debug( 'Session created (user=%s)', user )

@component.adapter(IUserLogonEvent)
def _new_session( event ):
	user = event.user
	request = event.request
	ip_addr = getattr( request, 'remote_addr' , None )
	platform = getattr( request, 'user_agent', None )
	timestamp = datetime.utcnow()

	process_event( 	_get_job_queue, _add_session,
					username=user.username,
					platform=platform,
					ip_addr=ip_addr,
					timestamp=timestamp )

def get_current_session_id( user ):
	db_sessions.get_current_session_id( user )

get_nti_session_id = get_current_session_id
