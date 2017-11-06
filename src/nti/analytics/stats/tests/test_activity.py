#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from datetime import timedelta

import unittest

from hamcrest import is_
from hamcrest import none
from hamcrest import assert_that

from ..activity import ActiveTimeStats

class FakeEvent(object):
    timestamp = None

class TestActiveTimeStats( unittest.TestCase ):

    def test_time_stats(self):
        stats = ActiveTimeStats()

        # python day indexes start 0=mon, 6=sun
        timestamps = {
            0: {
                11: 3,
                2: 6
            },
            1: {
                1: 3,
                4: 6
            },
            2: {
                7: 3,
                3: 6
            },
            3: {
                23: 3,
                1: 6
            },
            4: {
                0: 3,
                2: 6
            },
            5: {
                11: 3,
                2: 6
            },
            6: {
                13: 3,
                7: 6
            }
        }

        now = datetime.now()

        for day, hours in timestamps.items():
            for hour, count in hours.items():
                timestamp = now - timedelta(days=now.weekday())
                timestamp = now + timedelta(days=day+1)
                timestamp = timestamp.replace(hour=hour)
                for _ in range(count):
                    event = FakeEvent()
                    event.timestamp = timestamp
                    stats.process_event(event)

        for day, hours in timestamps.items():
            for hour, count in hours.items():
                assert_that(stats[day][hour].Count, is_(count))

        assert_that(stats[5][1].Count, is_(0))



