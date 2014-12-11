#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.intid.interfaces import IIntIdRemovedEvent

from nti.analytics.common import process_event

from nti.analytics.database import root_context as db_courses

from nti.analytics.identifier import CourseId

from nti.analytics import get_factory
from nti.analytics import DELETE_ANALYTICS

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue( DELETE_ANALYTICS )

def _delete_course( course_id ):
	db_courses.delete_course( course_id )
	logger.info( 'Deleted course (id=%s)', course_id )

@component.adapter( ICourseInstance, IIntIdRemovedEvent )
def _course_removed( entity, event ):
	course_id = CourseId.get_id( entity )
	process_event( _get_job_queue, _delete_course, course_id=course_id )

