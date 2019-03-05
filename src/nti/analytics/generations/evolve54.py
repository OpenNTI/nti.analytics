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
from sqlalchemy import inspect

from nti.analytics.database import get_analytics_db

from nti.analytics.generations.utils import do_evolve
from nti.analytics.generations.utils import mysql_column_exists


def evolve_job():
    setHooks()

    db = get_analytics_db()

    if db.defaultSQLite:
        return

    # Cannot use transaction with alter table scripts and mysql
    connection = db.engine.connect()
    mc = MigrationContext.configure( connection )
    op = Operations(mc)

    inspector=inspect(db.engine)
    schema = inspector.default_schema_name

    if not mysql_column_exists( connection, schema, 'VideoEvents', 'player_configuration' ):
        op.add_column( "VideoEvents", Column('player_configuration',
                                             Enum('inline', 'mediaviewer-full', 'mediaviewer-split', 'mediaviewer-transcript', validate_strings=True),
                                             nullable=True) )

    logger.info('Finished analytics migration %s, add player_configuration column for VideoEvents.', generation)

def evolve(context):
    """
    Evolve to generation 54
    """
    do_evolve( context, evolve_job, generation, with_library=False )
