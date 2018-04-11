#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import zope.intid

from datetime import datetime

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

from zope import component

from nti.analytics.database import scorm as db_scorm

from nti.analytics.scorm import get_scorm_package_launches
from nti.analytics.scorm import get_scorm_package_launches_for_ntiid

from nti.analytics.tests import test_session_id
from nti.analytics.tests import NTIAnalyticsTestCase

from nti.app.products.courseware_scorm.courses import SCORMCourseInstance

from nti.contenttypes.completion.tests.test_models import MockUser

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

test_user_ds_id = MockUser(u'78')


def _create_scorm_package_launch_event(user, course, metadata_ntiid, context_path):
    db_scorm.create_launch_record(user, course, metadata_ntiid, test_session_id, context_path, datetime.min)


class TestSCORMResourceViews(NTIAnalyticsTestCase):
    
    @WithMockDSTrans
    def test_launch_records(self):
        intids = component.getUtility(zope.intid.IIntIds)
        user = MockUser(u'test_user')
        course = SCORMCourseInstance()
        course_ntiid = u'tag:course_id'
        intids.register(course)
        metadata_ntiid = u'tag:metadata_id'
        assert_that(metadata_ntiid, is_not(none()))
        _create_scorm_package_launch_event(user, course, metadata_ntiid, [course_ntiid])
    
        # Empty
        results = get_scorm_package_launches_for_ntiid(metadata_ntiid + u'dne')
        assert_that(results, has_length(0))
    
        results = get_scorm_package_launches_for_ntiid(metadata_ntiid)
        assert_that(results, has_length(1))
        results = get_scorm_package_launches()
        assert_that(results, has_length(1))
        results = get_scorm_package_launches(user=user, root_context=course)
        assert_that(results, has_length(1))
