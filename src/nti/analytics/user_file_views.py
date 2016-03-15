#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from pyramid.threadlocal import get_current_request

from zope import component

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistoryItemFeedback

from nti.appserver.interfaces import IFileViewedEvent

from nti.dataserver.contenttypes.forums.interfaces import IPost

from nti.dataserver.interfaces import INote

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.traversal.traversal import find_interface

from nti.analytics.common import get_entity
from nti.analytics.common import process_event

from nti.analytics.sessions import get_nti_session_id

from nti.analytics.database import user_file_views as db_file_views

from nti.analytics import get_factory
from nti.analytics import RESOURCE_VIEW_ANALYTICS

get_user_file_views = db_file_views.get_user_file_views

def _get_resource_queue():
	factory = get_factory()
	return factory.get_queue( RESOURCE_VIEW_ANALYTICS )

def _get_file_view_root_obj( file_obj ):
	"""
	For a file view, we want the root object of types we allow
	(comments, feedback, or UGD).
	"""
	for iface in (INote, IUsersCourseAssignmentHistoryItemFeedback, IPost):
		root_obj = find_interface( file_obj, iface, strict=False )
		if root_obj is not None:
			return root_obj
	return None

def create_file_view( oid, nti_session, timestamp, username, referrer ):
	# XXX: We do not break this down by type, which would be an easy
	# way to then store by course.
	file_obj = find_object_with_ntiid( oid )
	user = get_entity( username )
	if file_obj is None or user is None:
		return

	# We do this here to not slow down the ds request processing.
	root_obj = _get_file_view_root_obj( file_obj )
	if root_obj is None:
		# We only want topic/post/feedback data; so if we find a course, we know it's
		# authored/uploaded files.
		return

	# Root obj creator should be our file owner, which we may not store in the ds.
	creator = root_obj.creator
	db_file_views.create_file_view( file_obj, nti_session, timestamp, user, referrer, creator )

@component.adapter(	IFileViewedEvent )
def _file_viewed( event ):
	nti_session = get_nti_session_id()
	username = event.request.remote_user
	referrer = event.request.referrer
	process_event( 	_get_resource_queue,
					create_file_view,
					event.context,
					nti_session=nti_session,
					timestamp=datetime.utcnow(),
					username=username,
					referrer=referrer )

	# Make sure we commit our job
	request = get_current_request()
	if request is not None:
		request.environ['nti.request_had_transaction_side_effects'] = True
