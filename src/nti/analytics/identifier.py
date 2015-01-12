#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid
from zope import component

from ZODB.interfaces import IBroken
from ZODB.POSException import POSError

from nti.ntiids import ntiids

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstance

from six import string_types

class _Identifier(object):
	"""
	Defines a unique identifier for objects that can be used for storage.
	It is vital that these ids can be used to look up the corresponding
	dataserver objects when the data is used to be displayed
	in the app or in reports.
	"""
	pass

intids = None
def _get_intid_utility():
	global intids
	if intids is None:
		intids = component.getUtility( zope.intid.IIntIds )
	return intids

class _DSIdentifier(_Identifier):

	@classmethod
	def get_id( cls, obj ):
		result = getattr( obj, '_ds_intid', None )
		return result or _get_intid_utility().getId( obj )

	@classmethod
	def get_object( cls, uid ):
		result = None
		try:
			obj = _get_intid_utility().queryObject( uid, default=None )
			if not IBroken.providedBy( obj ):
				result = obj
		except (TypeError, POSError):
			logger.warn( 'Broken object missing from course stream (id=%s)', uid )
		return result

class _NtiidIdentifier(_Identifier):

	@classmethod
	def get_id( cls, resource ):
		""" Resource could be a video or content piece. """
		if isinstance( resource, string_types ):
			result = resource
		else:
			result = getattr( resource, 'ntiid', None )
		return result

	@classmethod
	def get_object( cls, uid ):
		# TODO We may have to decode here.  Add tests.
		return ntiids.find_object_with_ntiid( uid )

class UserId(_DSIdentifier):
	pass

class SessionId(_Identifier):

	@classmethod
	def get_id( cls, nti_session ):
		# We're are getting session_ids here, which we will just return.
		return nti_session

class RootContextId(_NtiidIdentifier):

	@classmethod
	def get_id( cls, root_context ):
		""" Could be a course or content-package."""
		catalog_entry = ICourseCatalogEntry( root_context, None )
		result = getattr( catalog_entry, 'ntiid', None )

		if result is None:
			# Legacy course or content
			result = getattr( root_context, 'ContentPackageNTIID',
						getattr( root_context, 'ntiid', None ) )
		return result

	@classmethod
	def get_object( cls, ntiid ):
		obj = ntiids.find_object_with_ntiid( ntiid )
		# We may have:
		# 1. content package -> legacy course
		# 2. catalog entry -> new course
		# 3. content package / book
		# Adapt for 1,2; return 3.
		obj = ICourseInstance( obj, obj )
		return obj

class CommentId(_DSIdentifier):
	pass

class ForumId(_DSIdentifier):
	pass

class TopicId(_DSIdentifier):
	pass

class NoteId(_DSIdentifier):
	pass

class HighlightId(_DSIdentifier):
	pass

class ResourceId(_NtiidIdentifier):
	# Resource could be a video or content piece.
	pass

class BlogId(_DSIdentifier):
	pass

class ChatId(_DSIdentifier):
	pass

class DFLId(_DSIdentifier):
	pass

class FriendsListId(_DSIdentifier):
	pass

class SubmissionId(_DSIdentifier):
	pass

class QuestionSetId(_NtiidIdentifier):
	pass

class FeedbackId(_DSIdentifier):
	pass
