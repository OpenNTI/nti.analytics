#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.ntiids import ntiids

from nti.intid.interfaces import IIntIdAddedEvent
from nti.intid.interfaces import IIntIdRemovedEvent

from nti.dataserver import interfaces as nti_interfaces

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord
from nti.contenttypes.courses.enrollment import DefaultPrincipalEnrollments

from datetime import datetime

from nti.analytics import interfaces as analytics_interfaces
from nti.analytics.database import enrollments as db_enrollments

from .common import get_nti_session_id
from .common import process_event
from .common import get_entity
from .common import process_event

def _add_drop( oid, username, scope, nti_session=None, timestamp=None ):
	course = ntiids.find_object_with_ntiid( oid )
	user = get_entity( username )
	if 		user is not None \
		and course is not None:

		db_enrollments.create_course_drop( user, nti_session, timestamp, course )
		logger.debug( "User dropped (user=%s) (course=%s)",
					user,
					getattr( course, '__name__', course ) )

def _add_enrollment( oid, username, scope, nti_session=None, timestamp=None ):
	course = ntiids.find_object_with_ntiid( oid )
	user = get_entity( username )
	if 		user is not None \
		and course is not None:

		user = get_entity( username )
		enrollment_type = scope
		db_enrollments.create_course_enrollment( user, nti_session, timestamp, course, enrollment_type )
		logger.debug( "User enrollment (user=%s) (course=%s) (type=%s)",
					user,
					getattr( course, '__name__', course ),
					enrollment_type )

def _handle_event( record, to_call ):
	timestamp = datetime.utcnow()
	user = record.Principal
	username = getattr( user, 'username', None )
	course = record.CourseInstance
	scope = record.Scope

	nti_session = get_nti_session_id( get_entity( user ) )
	process_event( 	to_call,
					course,
					username=username,
					scope=scope,
					timestamp=timestamp,
					nti_session=nti_session )


@component.adapter( ICourseInstanceEnrollmentRecord, IIntIdAddedEvent )
def _enrolled( record, event ):
	_handle_event( record, _add_enrollment )

@component.adapter( ICourseInstanceEnrollmentRecord, IIntIdRemovedEvent )
def _dropped( record, event ):
	_handle_event( record, _add_drop )

def _user_enrollments( user ):
	enrollments = DefaultPrincipalEnrollments( user )
	for enrollment in enrollments.iter_enrollments():
		course = enrollment.CourseInstance
		username = user.username
		scope = enrollment.Scope
		process_event( _add_enrollment, course, username=username, scope=scope )

component.moduleProvides(analytics_interfaces.IObjectProcessor)
def init( obj ):
	result = False
	if 	nti_interfaces.IUser.providedBy(obj):
		_user_enrollments( obj )
		result = True
	return result
