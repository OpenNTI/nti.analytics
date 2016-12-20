#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zc.intid.interfaces import IBeforeIdRemovedEvent

from nti.contenttypes.courses.interfaces import ICourseInstance

from .common import process_event

from .database import root_context as db_courses

from .identifier import get_root_context_id

from . import DELETE_ANALYTICS

from . import get_factory

def _get_job_queue():
	factory = get_factory()
	return factory.get_queue(DELETE_ANALYTICS)

def _delete_course(course_id):
	db_courses.delete_course(course_id)
	logger.info('Deleted course (id=%s)', course_id)

@component.adapter(ICourseInstance, IBeforeIdRemovedEvent)
def _course_removed(entity, _):
	course_id = get_root_context_id(entity)
	process_event(_get_job_queue, _delete_course, course_id=course_id)
