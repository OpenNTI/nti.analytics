#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 34
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 34

from sqlalchemy import Column
from sqlalchemy import Integer

from .utils import do_evolve
from .utils import mysql_column_exists

from zope.component.hooks import setHooks
from alembic.operations import Operations
from alembic.migration import MigrationContext

from nti.analytics.database import get_analytics_db
from nti.analytics.database.locations import Location
from nti.analytics.database.locations import IpGeoLocation

def evolve_job():
    setHooks()

    db = get_analytics_db()

    # Don't do a migration on SQLite db
    if db.defaultSQLite:
        return

    # Cannot use transaction with alter table scripts and mysql
    connection = db.engine.connect()
    mc = MigrationContext.configure( connection )
    op = Operations( mc )
    originalTable = IpGeoLocation

    # Add location_id column
    if not mysql_column_exists( connection, originalTable.__tablename__, 'location_id' ):
        op.add_column( originalTable.__tablename__, Column('location_id',
                                                           Integer,
                                                           nullable=True,
                                                           index=True ) )

        # Populate the new table
        for record in db.session.query( originalTable ).yield_per( 1000 ):
                _latitude = getattr( record, 'latitude' )
                _longitude = getattr( record, 'longitude' )

                lat_str = str(round(_latitude, 4))
                long_str = str(round(_longitude, 4))

                # Check to see whether we've already created a row for this location
                existing_location = db.session.query( Location ).filter(
                                                                         Location.latitude == lat_str,
                                                                         Location.longitude == long_str
                                                                         ).first()

                if existing_location is None:
                    # We don't have an entry for this location yet.
                    new_location = Location( latitude=lat_str,
                                              longitude=long_str,
                                              city='',
                                              state='',
                                              country='' )
                    db.session.add( new_location )
                    db.session.flush()
                    # Set the location_id of the record to match the Location we just created
                    record.location_id = new_location.location_id
                    logger.info('Created location')
                else:
                    # We already know about this location.
                    # Set the location_id of the original table to the correct row.
                    record.location_id = existing_location.location_id
                    logger.info('Not a new location - linked existing location')

    logger.info( 'Finished analytics evolve (%s)', generation )

    """
    This migration moves location data (lat/long coordinates) to a separate table,
    Location. The Location table maintains the coordinates, making the 'latitude'
    and 'longitude' columns in IpGeoLocation obsolete, so another migration will
    be necessary to remove those at a future date. Also, since we now have a table
    dedicated to geographical locations, it would make sense to rename IpGeoLocation
    to IpLocation or something similar once we drop the lat/long columns.
    """

def evolve( context ):
    """
    Create the Locations table to store locations, and transfer lat/longs and labels to it.
    """
    do_evolve( context, evolve_job, generation )
