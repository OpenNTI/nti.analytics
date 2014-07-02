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
from .common import get_comment_root
from .common import process_event

from . import utils
from . import create_job
from . import get_job_queue
from . import interfaces as analytic_interfaces

def _add_session( db, session ):
	user = getattr( session, 'owner', None )
	timestamp = getattr( session, 'creation_time', datetime.utcnow() )
	# FIXME we don't have these attributes
	ip_addr = platform = version = None
	db.create_session( user, session, timestamp, ip_addr, platform, version )

@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionConnectedEvent )
def _session_created( session, event ) :
	process_event( _add_session, session )

def _remove_session( db, session, timestamp=None ):
	db.end_session( session, timestamp )

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
		from IPython.core.debugger import Tracer;Tracer()()
		# Store id here, how to lookup?
		# Or persist the whole session object if we can. 
		process_event( _add_session, obj )
		result = True
	return result
