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

from nti.dataserver.interfaces import IUser

from nti.contenttypes.courses.interfaces import ICourseInstanceEnrollmentRecord
from nti.contenttypes.courses.enrollment import DefaultPrincipalEnrollments

from datetime import datetime

from nti.analytics import get_factory
from nti.analytics import ENROLL_ANALYTICS

from nti.analytics.interfaces import IObjectProcessor

from nti.analytics.sessions import get_nti_session_id

from nti.analytics.database import enrollments as db_enrollments

from nti.analytics.common import get_root_context_name
from nti.analytics.common import process_event
from nti.analytics.common import get_entity

get_enrollments_for_course = db_enrollments.get_enrollments_for_course

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( ENROLL_ANALYTICS )

def _add_drop( oid, username, scope, nti_session=None, timestamp=None ):
	course = ntiids.find_object_with_ntiid( oid )
	user = get_entity( username )
	if 		user is not None \
		and course is not None:

		course_name = get_root_context_name( course )
		db_enrollments.create_course_drop( user, nti_session, timestamp, course )
		logger.debug( "User dropped (user=%s) (course=%s)",
					user,
					course_name )

def _add_enrollment( oid, username, scope, nti_session=None, timestamp=None ):
	course = ntiids.find_object_with_ntiid( oid )
	user = get_entity( username )
	if 		user is not None \
		and course is not None:

		enrollment_type = scope
		course_name = get_root_context_name( course )
		db_enrollments.create_course_enrollment( user, nti_session, timestamp, course, enrollment_type )
		logger.debug( "User enrollment (user=%s) (course=%s) (type=%s)",
					user,
					course_name,
					enrollment_type )

def _handle_event( record, to_call ):
	timestamp = datetime.utcnow()
	user = record.Principal
	username = getattr( user, 'username', None )
	course = record.CourseInstance
	scope = record.Scope

	nti_session = get_nti_session_id()
	process_event( _get_job_queue,
					to_call,
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
		process_event( _get_job_queue, _add_enrollment, course, username=username, scope=scope )

component.moduleProvides( IObjectProcessor )
def init( obj ):
	result = False
	if 	IUser.providedBy(obj):
		_user_enrollments( obj )
		result = True
	return result
