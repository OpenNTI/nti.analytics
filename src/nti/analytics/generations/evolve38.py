#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 38.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 38

from zope.component.hooks import setHooks

from sqlalchemy import Integer

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.assessments import SelfAssessmentViews
from nti.analytics.database.assessments import AssignmentViews
from nti.analytics.database.boards import TopicFavorites
from nti.analytics.database.boards import TopicLikes
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import TopicsViewed
from nti.analytics.database.boards import ForumCommentFavorites
from nti.analytics.database.boards import ForumCommentLikes
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.boards import ForumsCreated
from nti.analytics.database.resource_tags import BookmarksCreated
from nti.analytics.database.resource_tags import HighlightsCreated
from nti.analytics.database.resource_tags import NoteFavorites
from nti.analytics.database.resource_tags import NoteLikes
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NotesViewed
from nti.analytics.database.resource_views import CourseResourceViews
from nti.analytics.database.resource_views import VideoEvents
from nti.analytics.database.resource_views import VideoPlaySpeedEvents

from .utils import do_evolve

TABLES = [AssignmentViews,
	      SelfAssessmentViews,
	      ForumsCreated,
	      TopicsCreated,
	      ForumCommentsCreated,
	      TopicsViewed,
	      TopicFavorites,
	      TopicLikes,
	      ForumCommentFavorites,
	      ForumCommentLikes,
	      NotesCreated,
	      NotesViewed,
	      NoteLikes,
	      NoteFavorites,
	      HighlightsCreated,
	      BookmarksCreated,
	      VideoPlaySpeedEvents,
	      CourseResourceViews,
	      VideoEvents ]

def evolve_job():
	setHooks()
	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	nullable_col_name = 'course_id'

	for table in TABLES:
		op.alter_column( table.__tablename__, nullable_col_name, existing_type=Integer, nullable=True )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Make course_id column nullable.
	"""
	do_evolve( context, evolve_job, generation )
