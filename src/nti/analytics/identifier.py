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

from six import integer_types
from six import string_types

from nti.utils.property import Lazy

class _Identifier(object):
	"""
	Defines a unique identifier for objects that can be used for storage.
	It is vital that these ids can be used to look up the corresponding
	dataserver objects when the data is used to be displayed
	in the app or in reports.
	"""
	pass

class _DSIdentifier(_Identifier):

	@Lazy
	def intids(self):
		return component.getUtility( zope.intid.IIntIds )

	def get_id( self, obj ):
		result = getattr( obj, '_ds_intid', None )
		return result or self.intids.getId( obj )

class _NtiidIdentifier(_Identifier):

	def get_id(self, resource):
		""" Resource could be a video or content piece. """
		# Most likely, we'll have an ntiid here, which is what we want.
		if isinstance( resource, string_types ):
			result = resource
		else:
			result = getattr( resource, 'ntiid', None )
		return result


class UserId(_DSIdentifier):

	def get_id(self, user):
		if not user:
			return None
		# We may already have an integer id, use it.
		if isinstance( user, integer_types ):
			return user
		return super(UserId,self).get_id( user )

class SessionId(_Identifier):

	def get_id( self, nti_session ):
		# We're likely getting session_ids here, which we will just return.
		result = None
		if 		isinstance( nti_session, string_types ) \
			or 	nti_session is None:
			result = nti_session
		else:
			result = getattr( nti_session, 'session_id', None )

		return result

class CourseId(_DSIdentifier):

	def get_id( self, course ):
		# TODO ID needs to be unique by semester...Verify.
		if isinstance( course, ( integer_types, string_types ) ):
			return course
		return super(CourseId,self).get_id( course )

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

class FeedbackId(_DSIdentifier):
	pass
