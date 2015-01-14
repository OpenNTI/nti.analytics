#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time

from datetime import datetime

from unittest import TestCase

from hamcrest import assert_that
from hamcrest import not_none

from nti.analytics.common import timestamp_type

class TestTimestamp( TestCase ):
	"""
	Tests timestamp conversions.
	"""

	def test_timestamp(self):
		ts = time.time()
		result = timestamp_type( ts )
		assert_that( result, not_none() )

		date_ts = datetime.utcnow()
		result = timestamp_type( date_ts )
		assert_that( result, not_none() )

		# We even handle milliseconds
		ms_ts = 1421118460605
		result = timestamp_type( ms_ts )
		assert_that( result, not_none() )

