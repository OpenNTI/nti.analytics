#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.analytics_database.resource_views import UserFileUploadViewEvents

from nti.analytics.common import timestamp_type

from nti.analytics.identifier import get_ntiid_id

from nti.analytics.database import resolve_objects
from nti.analytics.database import get_analytics_db

from nti.analytics.database.mime_types import get_mime_type_id
from nti.analytics.database.mime_types import get_item_mime_type

from nti.analytics.database.query_utils import get_filtered_records

from nti.analytics.database.users import get_or_create_user

logger = __import__('logging').getLogger(__name__)


def create_file_view( file_obj, session_id, timestamp, user, referrer, creator ):
	file_ds_id = get_ntiid_id( file_obj )

	db = get_analytics_db()
	user_record = get_or_create_user( user )
	user_id = user_record.user_id
	timestamp = timestamp_type( timestamp )

	creator = get_or_create_user( creator )
	creator_id = creator.user_id
	mime_type = get_item_mime_type( file_obj )
	mime_type_id = get_mime_type_id( db, mime_type )

	file_view = UserFileUploadViewEvents(user_id=user_id,
										session_id=session_id,
										timestamp=timestamp,
										referrer=referrer,
										creator_id=creator_id,
										file_ds_id=file_ds_id,
										file_mime_type_id=mime_type_id )
	db.session.add( file_view )
	logger.info('Created file view event (user=%s) (file=%s)',
				user.username,
				getattr(file_obj, 'filename',
						getattr( file_obj, '__name__', '' )))
	return file_view


def _resolve_file_view(row, user=None):
	if user is not None:
		row.user = user
	return row


def get_user_file_views( user=None, **kwargs  ):
	results = get_filtered_records( user, UserFileUploadViewEvents, **kwargs )
	return resolve_objects( _resolve_file_view, results, user=user )

