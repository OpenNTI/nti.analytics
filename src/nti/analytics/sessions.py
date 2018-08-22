# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from datetime import datetime

from calendar import timegm as _calendar_timegm

from zope import component

from zope import interface

from nti.analytics import get_factory
from nti.analytics import SESSIONS_ANALYTICS

from nti.analytics_database.sessions import Sessions

from nti.analytics.common import get_entity
from nti.analytics.common import process_event

from nti.analytics.database import sessions as db_sessions

from nti.analytics.database.sessions import get_active_session_count
from nti.analytics.database.sessions import find_user_agent

from nti.analytics.interfaces import IAnalyticsSession
from nti.analytics.interfaces import IGeographicalLocation
from nti.analytics.interfaces import IAnalyticsSessionIdProvider

from nti.analytics.model import AnalyticsSession

from nti.analytics.stats.model import ActiveSessionStats

logger = __import__('logging').getLogger(__name__)

get_user_sessions = db_sessions.get_user_sessions
get_recent_user_sessions = db_sessions.get_recent_user_sessions


def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( SESSIONS_ANALYTICS )


def _end_session( username, session_id, timestamp=None ):
	user = get_entity( username )
	if session_id is not None:
		db_sessions.end_session( user, session_id, timestamp )
		logger.debug( 'Session ended (user=%s) (session_id=%s)', username, session_id )


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
	return new_session


def _process_end_session( username, session_id, timestamp ):
	process_event( _get_job_queue, _end_session,
						username=username,
						session_id=session_id,
						timestamp=timestamp )


def handle_end_session(username, session_id, timestamp=None):
	"""
	Handle the cleanup of the give analytics session_id.
	"""
	# This could be done synchronously, to be consistent, but we don't have to
	# currently.
	if session_id is not None:
		if timestamp is None:
			timestamp = datetime.utcnow()
		_process_end_session(username=username,
							 session_id=session_id,
							 timestamp=timestamp)


def update_session( session, user, user_agent=None, ip_addr=None ):
	"Create and update the given session based on information given and return."
	if session.SessionID is None:
		# Insert now
		new_session = _add_session(user, user_agent, ip_addr,
								  session.SessionEndTime,
								  start_time=session.SessionStartTime)
		session.SessionID = new_session.session_id
	elif session.SessionEndTime is not None:
		# Update end time by queuing job
		_process_end_session(username=user,
							 session_id=session.SessionID,
							 timestamp=session.SessionEndTime)
		session_record = db_sessions.get_session_by_id( session.SessionID )

		if session_record:
			# Update the start time with our information.
			start_time = session_record.start_time
			start_time = _calendar_timegm( start_time.utctimetuple() )
			session.SessionStartTime = start_time
		else:
			# Hmm, invalid information
			raise ValueError("Session has invalid values (sessionid=%s) (starttime=%s)"  %
							 (session.SessionID,
							  getattr(session_record, 'start_time', None)))
	return session


def get_current_session_id(event=None):
	"""
	Get the current analytics session id.
	"""
	result = None
	session_id_provider = IAnalyticsSessionIdProvider(event, None)
	if session_id_provider != None:
		result = session_id_provider.get_session_id()
	return result
get_nti_session_id = get_current_session_id


def _mktime(dt):
	return _calendar_timegm(dt.timetuple()) if dt else None


@component.adapter( Sessions )
@interface.implementer(IAnalyticsSession)
def _from_db_session(db_session):
	username = getattr(db_session.user, 'username', None)
	agent = getattr(find_user_agent(db_session.user_agent_id), 'user_agent', None)
	location = IGeographicalLocation(db_session, None)
	return AnalyticsSession(SessionID=db_session.SessionID,
				            SessionEndTime=_mktime(db_session.SessionEndTime),
			                SessionStartTime=_mktime(db_session.SessionStartTime),
			                Username=username,
			                UserAgent=agent,
			                GeographicalLocation=location)


def _active_session_count(**kwargs):
	count = get_active_session_count(**kwargs)
	return ActiveSessionStats(Count=count)
