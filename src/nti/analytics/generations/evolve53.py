#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 45.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

generation = 53

from nti.analytics.generations.evolve37 import evolve_job

from nti.analytics.generations.utils import do_evolve


def evolve(context):
	"""
	Expand our username column to 128 chars; re-running evolve 46
	which did not run in prod...
	"""
	do_evolve(context, evolve_job, generation, with_library=False)
