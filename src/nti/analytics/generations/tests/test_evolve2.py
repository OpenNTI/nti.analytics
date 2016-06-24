#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that

from nti.testing.matchers import verifiably_provides

from zope import component

from zope.component.hooks import site

from nti.analytics.tests import NTIAnalyticsTestCase
from nti.analytics.generations import evolve2

from nti.analytics import QUEUE_NAME as LEGACY_QUEUE_NAME
from nti.analytics.generations.evolve2 import QUEUE_NAMES

from nti.async import queue
from nti.async.interfaces import IQueue

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestEvolve2(NTIAnalyticsTestCase):

	@WithMockDSTrans
	def test_evolve2(self):

		conn = mock_dataserver.current_transaction
		class _context(object): 
			pass
		context = _context()
		context.connection = conn

		ds_folder = context.connection.root()['nti.dataserver']

		# Set up old state
		old_queue = queue.Queue()
		old_queue.__parent__ = ds_folder
		old_queue.__name__ = LEGACY_QUEUE_NAME
		lsm = ds_folder.getSiteManager()
		lsm.registerUtility(old_queue, provided=IQueue, name=LEGACY_QUEUE_NAME)

		evolve2.do_evolve(context)

		with site(ds_folder):
			for queue_name in QUEUE_NAMES:
				job_queue = component.getUtility(IQueue, name=queue_name)
				assert_that(job_queue, verifiably_provides(IQueue))
