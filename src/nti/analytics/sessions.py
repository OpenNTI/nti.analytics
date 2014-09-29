# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from .common import get_entity
from .common import process_event

from nti.analytics.database import sessions as db_sessions

from nti.analytics import get_factory
from nti.analytics import SESSIONS_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )

def _end_session( username, session_id, timestamp=None ):
	user = get_entity( username )
	if session_id is not None and user is not None:
		db_sessions.end_session( user, session_id, timestamp )
		logger.debug( 'Session ended (user=%s) (session_id=%s)', username )

def _add_session( username, user_agent, start_time, ip_addr, end_time=None ):
	if username:
		user = get_entity( username )
		new_session = db_sessions.create_session( user, user_agent, start_time, ip_addr, end_time )
		logger.debug( 'Session created (user=%s)', user )
		return new_session

def _do_new_session( username, request ):
	ip_addr = getattr( request, 'remote_addr' , None )
	user_agent = getattr( request, 'user_agent', None )
	timestamp = datetime.utcnow()

	process_event( 	_get_job_queue, _add_session,
					username=username,
					user_agent=user_agent,
					ip_addr=ip_addr,
					start_time=timestamp )

def handle_new_session( username, request ):
	_do_new_session( username, request )

def handle_end_session( username, session_id ):
	timestamp = datetime.utcnow()
	process_event( _get_job_queue, _end_session,
					username=username,
					session_id=session_id,
					timestamp=timestamp )

def handle_sessions( sessions, user, user_agent=None, ip_addr=None ):
	"Create new sessions based on information given and return, synchronously."
	for session in sessions:
		new_session = _add_session( user, user_agent, session.SessionStartTime, ip_addr, session.session_end_time )
		session.SessionId = new_session.session_id

def get_current_session_id( user ):
	result = None
	if user is not None:
		result = db_sessions.get_current_session_id( user )
	return result

get_nti_session_id = get_current_session_id


