#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generation 25.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

COLUMN_EXISTS_QUERY = 	"""
						SELECT *
						FROM information_schema.COLUMNS
						WHERE TABLE_SCHEMA = 'Analytics'
							AND TABLE_NAME = '%s'
							AND COLUMN_NAME = '%s'
						"""

def mysql_column_exists( con, table, column ):
	res = con.execute( COLUMN_EXISTS_QUERY % ( table, column ) )
	return res.scalar()
