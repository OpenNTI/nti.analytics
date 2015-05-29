#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 21.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 24

from zope.component.hooks import setHooks

from sqlalchemy import Column
from sqlalchemy import Boolean

from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.enrollments import CourseDrops
from nti.analytics.database.enrollments import CourseEnrollments
from nti.analytics.database.enrollments import CourseCatalogViews
from nti.analytics.database.assessments import AssignmentGrades
from nti.analytics.database.assessments import AssignmentsTaken
from nti.analytics.database.assessments import SelfAssessmentsTaken
from nti.analytics.database.assessments import AssignmentFeedback
from nti.analytics.database.blogs import BlogCommentFavorites
from nti.analytics.database.blogs import BlogCommentLikes
from nti.analytics.database.blogs import BlogCommentsCreated
from nti.analytics.database.blogs import BlogFavorites
from nti.analytics.database.blogs import BlogLikes
from nti.analytics.database.blogs import BlogsCreated
from nti.analytics.database.blogs import BlogsViewed
from nti.analytics.database.boards import TopicFavorites
from nti.analytics.database.boards import TopicLikes
from nti.analytics.database.boards import TopicsCreated
from nti.analytics.database.boards import TopicsViewed
from nti.analytics.database.boards import ForumCommentFavorites
from nti.analytics.database.boards import ForumCommentLikes
from nti.analytics.database.boards import ForumCommentsCreated
from nti.analytics.database.boards import ForumsCreated
from nti.analytics.database.social import ChatsInitiated
from nti.analytics.database.social import ChatsJoined
from nti.analytics.database.social import ContactsAdded
from nti.analytics.database.social import ContactsRemoved
from nti.analytics.database.social import DynamicFriendsListsMemberAdded
from nti.analytics.database.social import DynamicFriendsListsMemberRemoved
from nti.analytics.database.social import FriendsListsCreated
from nti.analytics.database.social import FriendsListsMemberAdded
from nti.analytics.database.social import FriendsListsMemberRemoved
from nti.analytics.database.resource_tags import BookmarksCreated
from nti.analytics.database.resource_tags import HighlightsCreated
from nti.analytics.database.resource_tags import NoteFavorites
from nti.analytics.database.resource_tags import NoteLikes
from nti.analytics.database.resource_tags import NotesCreated
from nti.analytics.database.resource_tags import NotesViewed
from nti.analytics.database.resource_views import CourseResourceViews
from nti.analytics.database.resource_views import VideoEvents

from ._utils import do_evolve

INDEX_EXISTS_QUERY = 	"""
						SHOW INDEX FROM Analytics.%s
						WHERE KEY_NAME = '%s';
						"""

COLUMN_EXISTS_QUERY = 	"""
						SELECT *
						FROM information_schema.COLUMNS
						WHERE TABLE_SCHEMA = 'Analytics'
							AND TABLE_NAME = '%s'
							AND COLUMN_NAME = '%s'
						"""

TABLES = [AssignmentFeedback,
	      AssignmentGrades,
	      AssignmentsTaken,
	      BlogCommentFavorites,
	      BlogCommentLikes,
	      BlogCommentsCreated,
	      BlogFavorites,
	      BlogLikes,
	      BlogsCreated,
	      BlogsViewed,
	      BookmarksCreated,
	      ChatsInitiated,
	      ChatsJoined,
	      ContactsAdded,
	      ContactsRemoved,
	      CourseCatalogViews,
	      CourseDrops,
	      CourseEnrollments,
	      CourseResourceViews,
	      ContactsRemoved,
	      DynamicFriendsListsMemberAdded,
	      DynamicFriendsListsMemberRemoved,
	      ForumCommentFavorites,
	      ForumCommentLikes,
	      ForumCommentsCreated,
	      ForumsCreated,
	      FriendsListsCreated,
	      FriendsListsMemberAdded,
	      FriendsListsMemberRemoved,
	      HighlightsCreated,
	      NoteFavorites,
	      NoteLikes,
	      NotesCreated,
	      NotesViewed,
	      SelfAssessmentsTaken,
	      TopicFavorites,
	      TopicLikes,
	      TopicsCreated,
	      TopicsViewed,
	      VideoEvents ]

def _index_exists( con, ix_name, table ):
	res = con.execute( INDEX_EXISTS_QUERY % ( table, ix_name ) )
	return res.scalar()

def _column_exists( con, table, column ):
	res = con.execute( COLUMN_EXISTS_QUERY % ( table, column ) )
	return res.scalar()

def evolve_job():
	setHooks()

	db = get_analytics_db()

	if db.defaultSQLite:
		return

	# Cannot use transaction with alter table scripts and mysql
	connection = db.engine.connect()
	mc = MigrationContext.configure( connection )
	op = Operations(mc)

	# Every table with timestamp
	for table_name in TABLES:
		ix_name = 'ix_%s_timestamp' % table_name.__tablename__.lower()
		if not _index_exists( connection, ix_name, table_name.__tablename__ ):
			op.create_index( ix_name, table_name.__tablename__, ['timestamp'] )

	column_name = 'is_late'

	if not _column_exists( connection, 'AssignmentsTaken', column_name ):
		op.add_column( 'AssignmentsTaken', Column('is_late', Boolean, nullable=True) )

	logger.info( 'Finished analytics evolve (%s)', generation )

def evolve(context):
	"""
	Add timestamp indexes. Add 'is_late' column to assignments.
	"""
	do_evolve( context, evolve_job, generation )
