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
from nti.analytics import FAIL_QUEUE

from nti.analytics.tests import NTIAnalyticsTestCase

class TestInstall(NTIAnalyticsTestCase):

	@mock_dataserver.WithMockDSTrans
	def test_install(self):
		queue_names = QUEUE_NAMES + [FAIL_QUEUE]

		for queue_name in queue_names:
			job_queue = component.getUtility( IQueue, name=queue_name )
			assert_that( job_queue, verifiably_provides( IQueue ) )
