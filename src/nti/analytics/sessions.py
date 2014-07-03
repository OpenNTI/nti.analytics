#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.intid import interfaces as intid_interfaces

from nti.socketio import interfaces as sio_interfaces

from nti.ntiids import ntiids

from datetime import datetime

from .common import get_creator
from .common import get_id_for_session
from .common import to_external_ntiid_oid
from .common import get_deleted_time
from .common import get_entity
from .common import get_comment_root
from .common import process_event

from . import utils
from . import create_job
from . import get_job_queue
from . import interfaces as analytic_interfaces

# Note: these are socket sessions, and may not be the best thing to store/listen-fo.
# 1. Not sure of the session lifecycle (new sessions clean out the old sessions)
# 2. Multiple created per *actual* session (though this may change)
# 3. Tied to #2, picking one of the open sessions for a user is arbitrary.

def _add_session( db, user, nti_session, timestamp, ip_addr=None, platform=None, version=None ):
	if nti_session:
		user = get_entity( user )
		db.create_session( user, nti_session, timestamp, ip_addr, platform, version )
		logger.debug( 'Session created (user=%s) (time=%s)', user, timestamp )

def _process_session_created( nti_session ):
	session_id = get_id_for_session( nti_session )
	user = getattr( nti_session, 'owner', None )
	user = get_entity( user )
	timestamp = getattr( nti_session, 'creation_time', datetime.utcnow() )
	# FIXME we don't have some of these attributes available to us.
	#ip_addr = platform = version = None
	process_event( _add_session, nti_session=session_id, user=user, timestamp=timestamp )

@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionConnectedEvent )
def _session_created( nti_session, event ):
	_process_session_created( nti_session )

def _remove_session( db, nti_session, user=None, timestamp=None ):
	if nti_session:
		db.end_session( nti_session, timestamp )
		logger.debug( 'Session destroyed (user=%s) (time=%s)', user, timestamp )

@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionDisconnectedEvent )
def _session_destroyed( nti_session, event ):
	# We could get 'last_heartbeat_time' as well
	session_id = get_id_for_session( nti_session )
	user = getattr( nti_session, 'owner', None )
	timestamp = datetime.utcnow()
	process_event( _remove_session, nti_session=session_id, user=user, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	# We probably only have live sessions at the migration instant.
	# Not sure if it's worth migrating them, but we can.
	result = False
	if 	sio_interfaces.ISocketSession.providedBy(obj):
		_process_session_created( obj )
		result = True
	return result
