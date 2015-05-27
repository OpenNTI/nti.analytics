#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 32.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 32

from zope.component.hooks import setHooks
from nti.analytics.database import get_analytics_db
from ._utils import store_video_duration_times

def do_evolve():
	setHooks()
	db = get_analytics_db()
	count, missing = store_video_duration_times( db, 'video_data_05152015.csv' )

	logger.info( 'Finished analytics evolve (%s) (count=%s) (missing=%s)',
				generation, count, missing )

def evolve(_):
	"""
	Store max_time_length video values from csv file.
	"""
	do_evolve()
