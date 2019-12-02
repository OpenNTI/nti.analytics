#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 56.

.. $Id$
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

generation = 56

from zope.component.hooks import setHooks

from alembic.operations import Operations
from alembic.migration import MigrationContext

from sqlalchemy import Enum

from nti.analytics.database import get_analytics_db

from nti.analytics.generations.utils import do_evolve

logger = __import__('logging').getLogger(__name__)


def evolve_job():
    setHooks()

    db = get_analytics_db()

    if db.defaultSQLite:
        return

    # Cannot use transaction with alter table scripts and mysql
    connection = db.engine.connect()
    mc = MigrationContext.configure( connection )
    op = Operations(mc)

    op.alter_column('VideoEvents', 'player_configuration',
                     type_=Enum('inline', 'mediaviewer-full', 'mediaviewer-split', 'mediaviewer-transcript', 'media-modal', validate_strings=True),
                     existing_type=Enum('inline', 'mediaviewer-full', 'mediaviewer-split', 'mediaviewer-transcript', validate_strings=True))

    logger.info('Finished analytics migration %s, add media-modal for player_configuration column for VideoEvents.', generation)

def evolve(context):
    """
    Evolve to generation 56
    """
    do_evolve( context, evolve_job, generation, with_library=False )
