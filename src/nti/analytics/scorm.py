#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.app.products.courseware_scorm.interfaces import ISCORMPackageLaunchEvent

from .database import scorm as db_scorm

from .sessions import get_nti_session_id


def _add_launch_record(user, course, metadata, nti_session, timestamp):
    context_path = [course.ntiid]
    db_scorm.create_launch_record(user, course, metadata, nti_session, context_path, timestamp)
    

@component.adapter(ISCORMPackageLaunchEvent)
def _scorm_package_launched(event):
    nti_session = get_nti_session_id()
    _add_launch_record(event.user, event.course, event.metadata, nti_session, event.timestamp)

