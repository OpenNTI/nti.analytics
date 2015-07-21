#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 33.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 33

from zope.component.hooks import setHooks

from sqlalchemy import Integer
from sqlalchemy import Column

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

from ._utils import do_evolve
from ._utils import mysql_column_exists

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

	new_column_name = 'entity_root_context_id'
	nullable_col_name = 'course_id'

	for table in TABLES:
		if not mysql_column_exists( connection, table.__tablename__, new_column_name ):
			op.add_column( table.__tablename__, Column( new_column_name, Integer,
									nullable=True, index=True, autoincrement=False) )
			op.alter_column( table.__tablename__, nullable_col_name, existing_type=Integer, nullable=True )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve( context ):
	"""
	Add an entity root context column; make course_id column nullable.
	"""
	do_evolve( context, evolve_job, generation )
