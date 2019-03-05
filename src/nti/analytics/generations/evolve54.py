#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 54.

.. $Id$
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 54

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Interval

from nti.analytics.database import get_analytics_db


COLUMN_EXISTS_QUERY =   """
                        SELECT *
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = 'Analytics'
                            AND TABLE_NAME = '%s'
                            AND COLUMN_NAME = '%s'
                        """


def _column_exists( con, table, column ):
    res = con.execute( COLUMN_EXISTS_QUERY % ( table, column ) )
    return res.scalar()

def do_evolve():
    setHooks()

    db = get_analytics_db()

    if db.defaultSQLite and db.dburi == "sqlite://":
        # In-memory mode for dev
        return

    # Cannot use transaction with alter table scripts and mysql
    connection = db.engine.connect()
    mc = MigrationContext.configure( connection )
    op = Operations(mc)

    if not _column_exists( connection, 'VideoEvents', 'player_configuration' ):
        op.add_column( "VideoEvents", Column('player_configuration',
                                             Enum('inline', 'mediaviewer-full', 'mediaviewer-split', 'mediaviewer-transcript', validate_strings=True),
                                             nullable=True) )

    logger.info('Finished analytics migration %s, add player_configuration column for VideoEvents.', generation)

def evolve(context):
    """
    Evolve to generation 54
    """
    do_evolve()
