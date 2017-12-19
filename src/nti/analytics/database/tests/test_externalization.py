#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from datetime import datetime

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import ends_with

from unittest import TestCase

from nti.analytics.database import resource_views as db_views

from nti.analytics.database.resources import Resources

from nti.analytics.tests import NTIAnalyticsTestCase

from nti.analytics_database.resource_views import CourseResourceViews

from nti.analytics_database.mime_types import FileMimeTypes # side effects in the ORM?

from nti.externalization.externalization import to_external_object

class TestExternalization(NTIAnalyticsTestCase):

    def test_resource_view(self):
        view = CourseResourceViews()
        view.session_id = 1
        view.timestamp = datetime.now()

        external = to_external_object(view, name='summary')
        assert_that(external, has_entries('MimeType', ends_with('.analytics.vieweventsummary'),
                                          'SessionID', 1))


