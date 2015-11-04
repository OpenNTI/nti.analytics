# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics.database import locations as db_locations

update_missing_locations = db_locations.update_missing_locations
get_location_list = db_locations.get_location_list

