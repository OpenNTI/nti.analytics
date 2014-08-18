#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nti.testing.matchers import verifiably_provides

from zope import component

from nti.dataserver.tests import mock_dataserver

from nti.async.interfaces import IQueue

from nti.analytics import QUEUE_NAMES

from nti.analytics.tests import NTIAnalyticsTestCase

class TestInstall(NTIAnalyticsTestCase):

	@mock_dataserver.WithMockDSTrans
	def test_install(self):
		for queue_name in QUEUE_NAMES:
			job_queue = component.getUtility( IQueue, name=queue_name )
			assert_that( job_queue, verifiably_provides( IQueue ) )
