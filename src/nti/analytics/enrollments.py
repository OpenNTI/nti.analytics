#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent import interfaces as lce_interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.ntiids import ntiids
from nti.intid import interfaces as intid_interfaces
from nti.app.products.courseware import interfaces as course_interfaces
from nti.store import interfaces as store_interfaces
from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.app.products.courseware.interfaces import ICourseCatalog
from nti.dataserver.users import Community

from datetime import datetime

from .common import process_event

from . import create_job
from . import get_job_queue
from . import interfaces as analytics_interfaces

from .common import get_creator
from .common import get_nti_session_id
from .common import get_deleted_time
from .common import get_comment_root
from .common import get_course
from .common import process_event
from .common import get_created_timestamp
from .common import get_entity
from .common import IDLookup

FOR_CREDIT = 'FOR_CREDIT'
OPEN = 'OPEN'

def _add_drop( db, user, community, timestamp=None, nti_session=None ):
	user = get_entity( user )
	community = get_entity( community )
	course = ICourseInstance( community, None )
	if 		user is not None \
		and course is not None:
		
		db.create_course_drop( user, nti_session, timestamp, course )
		logger.debug( "User dropped (user=%s) (course=%s)", user, course )

def _get_enrollment_type( user, course ):
	# course.instructors are in this set
	# TODO Expensive. Can we do better?
	restricted_id = course.LegacyScopes['restricted']
	restricted = get_entity(restricted_id) if restricted_id else None
	
	restricted_usernames = ({x.lower() for x in nti_interfaces.IEnumerableEntityContainer(restricted).iter_usernames()}
							if restricted is not None
							else set())
	is_for_credit = user.username in restricted_usernames
	return FOR_CREDIT if is_for_credit else OPEN

def _do_enroll( db, user, course, nti_session=None, timestamp=None ):
	enrollment_type = _get_enrollment_type( user, course )
	db.create_course_enrollment( user, nti_session, timestamp, course, enrollment_type )
	logger.debug( "User enrollment (user=%s) (course=%s) (type=%s)", user, course, enrollment_type )

def _add_enrollment( db, user, community, timestamp=None, nti_session=None ):
	user = get_entity( user )
	community = get_entity( community )
	# Are all communities course memberships?
	course = ICourseInstance( community, None )
	if 		user is not None \
		and course is not None:
		
		_do_enroll( db, user, course, nti_session, timestamp )

def _handle_event( event, to_call ):	
	timestamp = datetime.utcnow()
	source = getattr(event.object, 'username', event.object)
	target = event.target
	# We only listen for Community targeted DFL joins
	if not nti_interfaces.ICommunity.providedBy( target ):
		return
	
	target = getattr(target, 'username', target)
	
	nti_session = get_nti_session_id( get_entity( source ) )
	process_event( 	to_call, 
					user=source,
					community=target, 
					timestamp=timestamp, 
					nti_session=nti_session )
			

@component.adapter(nti_interfaces.IStartDynamicMembershipEvent)
def _enrolled(event):
	from IPython.core.debugger import Tracer;Tracer()()
	_handle_event( event, _add_enrollment )

@component.adapter(nti_interfaces.IStopDynamicMembershipEvent)
def _dropped(event):
	_handle_event( event, _add_drop )

def _user_enrollments( user ):
	communities = getattr( user, 'usernames_of_dynamic_memberships', list() )
	user = getattr( user, 'username', None )
	for community in communities:
		process_event( _add_enrollment, user=user, community=community )

component.moduleProvides(analytics_interfaces.IObjectProcessor)
def init( obj ):
	result = False
	if 	nti_interfaces.IUser.providedBy(obj):
		_user_enrollments( obj )
		result = True	
	return result
