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
from .common import get_nti_session
from .common import to_external_ntiid_oid
from .common import get_deleted_time
from .common import get_entity
from .common import get_comment_root
from .common import process_event

from . import utils
from . import create_job
from . import get_job_queue
from . import interfaces as analytic_interfaces

def _add_session( db, oid ):
	nti_session = ntiids.find_object_with_ntiid( oid )
	if nti_session:
		user = getattr( nti_session, 'owner', None )
		user = get_entity( user )
		timestamp = getattr( nti_session, 'creation_time', datetime.utcnow() )
		# FIXME we don't have these attributes
		ip_addr = platform = version = None
		db.create_session( user, nti_session, timestamp, ip_addr, platform, version )
		logger.debug( 'Session created (user=%s) (time=%s)', user, timestamp )

@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionConnectedEvent )
def _session_created( session, event ):
	# FIXME If these sessions will not be stored long term in the DS, we'll 
	# need to pass the object (or values) along.  If not, we may lose them.
	process_event( _add_session, session )

def _remove_session( db, oid, timestamp=None ):
	nti_session = ntiids.find_object_with_ntiid( oid )
	if nti_session:
		user = getattr( nti_session, 'owner', None )
		user = get_entity( user )
		db.end_session( nti_session, timestamp )
		logger.debug( 'Session destroyed (user=%s) (time=%s)', user, timestamp )

@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionDisconnectedEvent )
def _session_destroyed( session, event ):
	# We could get 'last_heartbeat_time' as well
	timestamp = datetime.utcnow()
	process_event( _remove_session, session, timestamp=timestamp )

component.moduleProvides(analytic_interfaces.IObjectProcessor)

def init( obj ):
	# We probably only have live sessions at the migration instant.
	# Not sure if it's worth migrating them, but we can.
	result = False
	if 	sio_interfaces.ISocketSession.providedBy(obj):
		process_event( _add_session, obj )
		result = True
	return result
