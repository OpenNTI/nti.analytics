# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from calendar import timegm as _calendar_timegm

from pyramid.threadlocal import get_current_request

from zope import component
from zope.event import notify

from nti.appserver.interfaces import IUserLogoutEvent

from nti.analytics import get_factory
from nti.analytics import has_analytics
from nti.analytics import SESSIONS_ANALYTICS

from nti.analytics.common import get_entity
from nti.analytics.common import process_event

from nti.analytics.database import sessions as db_sessions

from nti.analytics.recorded.interfaces import AnalyticsSessionRecordedEvent

ANALYTICS_SESSION_COOKIE_NAME = str( 'nti.da_session' )
ANALYTICS_SESSION_HEADER = str( 'x-nti-da-session' )

def _get_session_id_from_val( val ):
	if val is None:
		return None

	try:
		result = int( val )
	except ValueError:
		# Shouldn't get here.
		logger.warn( 'Received analytics session id that is not an int (%s)', val )
		result = None
	return result

def _get_header_id( request ):
	val = request.headers.get( ANALYTICS_SESSION_HEADER )
	return _get_session_id_from_val( val )

def _get_cookie_id( request ):
	val = request.cookies.get( ANALYTICS_SESSION_COOKIE_NAME )
	return _get_session_id_from_val( val )

def _set_cookie( request, new_session ):
	# If we have current session, fire an event to kill it.
	# TODO: Is this what we want?  What about multiple tabs?
	# Will we inadvertantly kill open sessions?
	old_id = _get_cookie_id( request )
	if old_id is not None:
		user = get_entity( request.remote_user )
		if user is not None:
			_process_end_session( user.username, old_id, datetime.utcnow() )

	request.response.set_cookie( ANALYTICS_SESSION_COOKIE_NAME,
								value=str( new_session.session_id ),
								overwrite=True )

def _remove_cookie( request ):
	request.response.delete_cookie( ANALYTICS_SESSION_COOKIE_NAME )

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )

def _end_session( username, session_id, timestamp=None ):
	user = get_entity( username )
	if session_id is not None:
		session = db_sessions.end_session( user, session_id, timestamp )
		logger.debug( 'Session ended (user=%s) (session_id=%s)', username, session_id )
		if session:
			notify( AnalyticsSessionRecordedEvent( user, session.start_time, session.end_time, timestamp ))

def _add_session( username, user_agent, ip_addr, end_time=None, start_time=None, timestamp=None ):
	if username:
		# Backwards compat
		start_time = start_time or timestamp
		user = get_entity( username )
		new_session = db_sessions.create_session( user, user_agent, start_time, ip_addr, end_time )
		logger.debug( 'Session created (user=%s)', user )
		return new_session

def handle_new_session( username, request ):
	""" Create a new session, synchronously. """
	ip_addr = getattr( request, 'remote_addr' , None )
	user_agent = getattr( request, 'user_agent', None )
	timestamp = datetime.utcnow()

	new_session = _add_session(username=username,
						user_agent=user_agent,
						ip_addr=ip_addr,
						start_time=timestamp )
	_set_cookie( request, new_session )

def _process_end_session( username, session_id, timestamp ):
	process_event( _get_job_queue, _end_session,
						username=username,
						session_id=session_id,
						timestamp=timestamp )


@component.adapter( IUserLogoutEvent )
def _user_logout_event( event ):
	"""
	When a user logs out, terminate any sessions tied to the request.
	We only do this for cookies (e.g. webapp/mobile) since other clients
	manage their own sessions explicitly.
	"""
	cookie_id = _get_cookie_id( event.request )

	if cookie_id is not None:
		user = event.user
		username = getattr( user, 'username', None )
		if username is None:
			username = getattr( event.request, 'remote_user', None )
		timestamp = datetime.utcnow()
		_process_end_session( username, cookie_id, timestamp )

def handle_end_session( username, request, timestamp=None ):
	# This could be done synchronously, to be consistent, but we don't have to currently.
	session_id = _get_cookie_id( request )
	if session_id is not None:
		if timestamp is None:
			timestamp = datetime.utcnow()
		_process_end_session( username=username, session_id=session_id, timestamp=timestamp )
		_remove_cookie( request )

def update_session( session, user, user_agent=None, ip_addr=None ):
	"Create and update the given session based on information given and return. "
	if session.SessionID is None:
		# Insert now
		new_session = _add_session( user, user_agent, ip_addr, session.SessionEndTime, start_time=session.SessionStartTime )
		session.SessionID = new_session.session_id
	elif session.SessionEndTime is not None:
		# Update end time by queuing job
		_process_end_session( username=user, session_id=session.SessionID, timestamp=session.SessionEndTime )
		session_record = db_sessions.get_session_by_id( session.SessionID )

		if session_record:
			# Update the start time with our information.
			start_time = session_record.start_time
			start_time = _calendar_timegm( start_time.utctimetuple() )
			session.SessionStartTime = start_time
		else:
			# Hmm, invalid information
			raise ValueError( "Session has invalid values (sessionid=%s) (starttime=%s)"  %
							( 	session.SessionID,
								getattr( session_record, 'start_time', None ) ) )
	return session

def get_current_session_id( event=None ):
	# Here is what we look for, in order:
	# 1. A session id attached to the incoming event (probably ipad only)
	# 2. A header on the request, (also ipad)
	# 3. A cookie, which should be from webapp, that we can also validate.

	given_session_id = getattr( event, 'SessionID', None )
	if given_session_id is not None:
		return given_session_id

	request = get_current_request()

	if 		request is None \
		or 	not has_analytics():
		return None

	result = header_id = _get_header_id( request )

	if header_id is None:
		result = _get_cookie_id( request )

	return result

get_nti_session_id = get_current_session_id


