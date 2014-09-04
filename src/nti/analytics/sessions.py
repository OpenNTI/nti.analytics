# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from datetime import datetime

from .common import get_entity
from .common import process_event

from nti.appserver.interfaces import IUserLogonEvent

from nti.analytics.database import sessions as db_sessions

from nti.analytics import get_factory
from nti.analytics import SESSIONS_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )

def _add_session( username, user_agent, timestamp, ip_addr ):
	if username:
		user = get_entity( username )
		db_sessions.create_session( user, user_agent, timestamp, ip_addr )
		logger.debug( 'Session created (user=%s)', user )

def _do_new_session( username, request ):
	ip_addr = getattr( request, 'remote_addr' , None )
	user_agent = getattr( request, 'user_agent', None )
	timestamp = datetime.utcnow()

	process_event( 	_get_job_queue, _add_session,
					username=username,
					user_agent=user_agent,
					ip_addr=ip_addr,
					timestamp=timestamp )

@component.adapter(IUserLogonEvent)
def _new_session( event ):
	# FIXME Hmm, login events are GETs
	user = event.user
	request = event.request
	_do_new_session( user.username, request )

def handle_new_session( username, request ):
	_do_new_session( username, request )

def get_current_session_id( user ):
	result = None
	if user is not None:
		result = db_sessions.get_current_session_id( user )
	return result

get_nti_session_id = get_current_session_id


