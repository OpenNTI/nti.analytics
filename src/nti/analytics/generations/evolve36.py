#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 33.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 36

from zope.component.hooks import setHooks

from nti.analytics.database import get_analytics_db

from nti.analytics.database.resource_tags import _get_sharing_enum

from nti.analytics.database.root_context import get_root_context

from nti.analytics_database.resource_tags import NotesCreated

from nti.analytics.identifier import NoteId

from ._utils import do_evolve

seen = set()

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	global seen
	# Update sharing
	# This may be wonky in alpha since we have one db for all sites.
	updated_count = 0
	for record in db.session.query( NotesCreated ).yield_per( 1000 ):
		if record.course_id is None or record.note_ds_id is None:
			continue

		if record.note_ds_id in seen:
			continue

		course = get_root_context( record.course_id )
		if course is None:
			continue

		note = NoteId.get_object( record.note_ds_id )
		if note is None:
			continue

		# Add to our cache so we don't check this object for
		# other sites
		seen.add( record.note_ds_id )

		sharing = _get_sharing_enum(note, course)
		record.sharing = sharing
		updated_count += 1

	logger.info( 'Finished analytics evolve (%s) (updated=%s)', generation, updated_count )

def evolve( context ):
	"""
	Expand and correct the sharing scope information in notes.
	"""
	do_evolve( context, evolve_job, generation, with_library=True )
