#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 15.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 16

import zope.intid
from zope import component
from zope.component.hooks import site, setHooks

from nti.analytics.database import get_analytics_db
from nti.analytics.database.root_context import Courses

from nti.analytics.identifier import RootContextId

def do_evolve(context):
	setHooks()

	db = get_analytics_db()

	# Swap out ds_intids for ntiids
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		intids = component.getUtility( zope.intid.IIntIds )
	all_courses = db.session.query( Courses ).all()

	for course in all_courses:
		course_ds_intid = course.context_ds_id
		try:
			course_ds_intid = int( course_ds_intid )
		except (TypeError,ValueError):
			# Already converted or missing
			continue

		course_obj = intids.queryObject( course_ds_intid, default=None )
		if course_obj is not None:
			course_ntiid = RootContextId.get_id( course_obj )
			if course_ntiid:
				course.context_ds_id = course_ntiid
		else:
			# Was deleted
			course.context_ds_id = None

	logger.info( 'Finished analytics evolve16' )

def evolve(context):
	"""
	Converts course ids from ds_intids to ntiids.
	"""
	do_evolve(context)
