#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 41

from nti.analytics.generations.evolve36 import evolve as do_evolve_36

def evolve( context ):
	"""
	Fix missing sharing data in NotesCreated.
	"""
	do_evolve_36( context )
