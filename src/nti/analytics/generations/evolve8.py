#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 8.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 8

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

def _remove_invalid_records( db ):
	# Note: Failed due to foreign key references.
	# Now addressed by evolve10.
	pass

def do_evolve(context):
	setHooks()

	db = get_analytics_db()
	if db.defaultSQLite and db.dburi == "sqlite://":
		# In-memory mode for dev
		return

	_remove_invalid_records( db )


def evolve(context):
	"""
	Evolve to generation 8
	"""
	do_evolve(context)
