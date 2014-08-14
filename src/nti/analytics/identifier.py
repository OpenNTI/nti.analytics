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

from nti.ntiids import ntiids

from nti.utils.property import Lazy

from six import string_types

class _Singleton(object):
	_instances = {}
	def __new__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(_Singleton, cls).__new__(cls, *args, **kwargs)
		return cls._instances[cls]

class _Identifier(_Singleton):
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

	def get_object( self, id ):
		return self.intids.getObject( id )

class _NtiidIdentifier(_Identifier):

	def get_id(self, resource):
		""" Resource could be a video or content piece. """
		if isinstance( resource, string_types ):
			result = resource
		else:
			result = getattr( resource, 'ntiid', None )
		return result

	def get_object( self, id ):
		return ntiids.find_object_with_ntiid( id )

class UserId(_DSIdentifier):
	pass

class SessionId(_Identifier):

	def get_id( self, nti_session ):
		# We're likely getting session_ids here, which we will just return.
		result = getattr( nti_session, 'session_id', nti_session )
		return result

class CourseId(_DSIdentifier):
	# TODO ID needs to be unique by semester...Verify.
	pass

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
