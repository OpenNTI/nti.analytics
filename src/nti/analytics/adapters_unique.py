#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.intid
from zope import component
from zope import interface

from nti.assessment import interfaces as asm_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.contentsearch import interfaces as search_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from . common import to_external_ntiid_oid
from . import interfaces as graph_interfaces

def get_ntiid(obj):
	return getattr(obj, 'NTIID', getattr(obj, 'ntiid'))

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(interface.Interface)
class _GenericUniqueAttributeAdpater(object):

	key = value = None

	def __init__(self, obj):
		self.obj = obj

	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _IntIDUniqueAttributeAdpater(_GenericUniqueAttributeAdpater):

	key = "intid"

	@property
	def value(self):
		intids = component.getUtility(zope.intid.IIntIds)
		result = intids.queryId(self.obj)
		return result

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _OIDUniqueAttributeAdpater(_GenericUniqueAttributeAdpater):

	key = "oid"

	@property
	def value(self):
		result = to_external_ntiid_oid(self.obj)
		return result

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(nti_interfaces.IEntity)
class _EntityUniqueAttributeAdpater(_GenericUniqueAttributeAdpater):

	key = "username"

	@property
	def value(self):
		return self.obj.username

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(frm_interfaces.ITopic)
class _TopicUniqueAttributeAdpater(_GenericUniqueAttributeAdpater):

	key = "oid"

	@property
	def value(self):
		return self.obj.NTIID

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(frm_interfaces.IHeadlinePost)
class _HeadlinePostUniqueAttributeAdpater(_TopicUniqueAttributeAdpater):

	def __init__(self, obj):
		super(_HeadlinePostUniqueAttributeAdpater, self).__init__(obj.__parent__)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(lib_interfaces.IContentUnit)
class _ContentUnitAttributeAdpater(_OIDUniqueAttributeAdpater):

	@property
	def value(self):
		return self.obj.ntiid

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _NTIIDUniqueAttributeAdpater(_OIDUniqueAttributeAdpater):

	key = "oid"

	@property
	def value(self):
		return get_ntiid(self.obj)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(graph_interfaces.IContainer)
class _ContainerUniqueAttributeAdpater(_OIDUniqueAttributeAdpater):

	@property
	def value(self):
		return self.obj.id

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(search_interfaces.ISearchQuery)
class _SearchQueryUniqueAttributeAdpater(_GenericUniqueAttributeAdpater):

	key = "term"

	@property
	def value(self):
		# TODO: Better way?
		result = self.obj.term.lower()
		return result

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _EndRelationshipUniqueAttributeAdpater(_OIDUniqueAttributeAdpater):

	def __init__(self, _from, _to, _rel):
		# a relationship is identified by the end object oid
		super(_EndRelationshipUniqueAttributeAdpater, self).__init__(_to)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _EntityObjectRelationshipUniqueAttributeAdpater(object):

	def __init__(self, entity, to, rel):
		self.to = to
		self.rel = rel
		self.entity = entity

	@property
	def key(self):
		return self.entity.username

	@property
	def value(self):
		oid = to_external_ntiid_oid(self.to)
		result = '%s,%s' % (self.rel, oid)
		return result

	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

_CommentRelationshipUniqueAttributeAdpater = _EntityObjectRelationshipUniqueAttributeAdpater

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _ObjectEntityRelationshipUniqueAttributeAdpater(object):

	def __init__(self, obj, entity, rel):
		self.obj = obj
		self.rel = rel
		self.entity = entity

	@property
	def key(self):
		return to_external_ntiid_oid(self.obj)

	@property
	def value(self):
		result = '%s,%s' % (self.rel, self.entity.username)
		return result

	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _RelationshipUniqueAttributeAdpater(object):

	def __init__(self, _from, _to, _rel):
		self._to = _to
		self._rel = _rel
		self._from = _from

	@property
	def key(self):
		return self._from.username

	@property
	def value(self):
		result = '%s,%s' % (self._rel, self._to.username)
		return result
	
	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

_FollowUniqueAttributeAdpater = _RelationshipUniqueAttributeAdpater
_FriendshipUniqueAttributeAdpater = _RelationshipUniqueAttributeAdpater
_TargetMembershipUniqueAttributeAdpater = _RelationshipUniqueAttributeAdpater

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
class _ObjectRelationshipUniqueAttributeAdpater(object):

	def __init__(self, child, parent, rel):
		self.rel = rel
		self.child = child
		self.parent = parent

	@property
	def key(self):
		return to_external_ntiid_oid(self.child)

	@property
	def value(self):
		oid = to_external_ntiid_oid(self.parent)
		result = '%s,%s' % (self.rel, oid)
		return result

	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

class _NTIIDMembershipUniqueAttributeAdpater(object):

	def __init__(self, _from, _to, _rel):
		self._to = _to
		self._rel = _rel
		self._from = _from

	@property
	def key(self):
		return get_ntiid(self._from)

	@property
	def value(self):
		result = '%s,%s' % (self._rel, get_ntiid(self._to))
		return result

	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(asm_interfaces.IQuestion,
				   asm_interfaces.IQuestionSet,
				   graph_interfaces.IMemberOf)
class _QuestionMembershipUniqueAttributeAdpater(_NTIIDMembershipUniqueAttributeAdpater):
	pass

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(asm_interfaces.IQuestionSet,
				   asm_interfaces.IQAssignment,
				   graph_interfaces.IMemberOf)
class _AssignmentMembershipUniqueAttributeAdpater(_NTIIDMembershipUniqueAttributeAdpater):
	pass

@component.adapter(nti_interfaces.IUser,
				   nti_interfaces.ILikeable,
				   graph_interfaces.ILike)
class _LikeUniqueAttributeAdpater(_EntityObjectRelationshipUniqueAttributeAdpater):
	pass

@component.adapter(nti_interfaces.IUser,
				   nti_interfaces.IRatable,
				   graph_interfaces.IRate)
class _RateUniqueAttributeAdpater(_EntityObjectRelationshipUniqueAttributeAdpater):
	pass

@component.adapter(nti_interfaces.IUser,
				   nti_interfaces.IFlaggable,
				   graph_interfaces.IFlagged)
class _FlaggUniqueAttributeAdpater(_EntityObjectRelationshipUniqueAttributeAdpater):
	pass

@component.adapter(nti_interfaces.IUser,
				   nti_interfaces.IThreadable,
				   graph_interfaces.IReply)
class _InReplyToUniqueAttributeAdpater(_EntityObjectRelationshipUniqueAttributeAdpater):
	pass

_AuthorshipUniqueAttributeAdpater = _EntityObjectRelationshipUniqueAttributeAdpater
_AssessedRelationshipUniqueAttributeAdpater = _EntityObjectRelationshipUniqueAttributeAdpater

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(nti_interfaces.IUser,
				   asm_interfaces.IQAssignment,
				   graph_interfaces.ITakeAssessment)
class _AssignmentTakenUniqueAttributeAdpater(object):

	def __init__(self, entity, asm, rel):
		self.asm = asm
		self.rel = rel
		self.entity = entity

	@property
	def key(self):
		return self.entity.username

	@property
	def value(self):
		ntiid = get_ntiid(self.asm)
		result = '%s,%s' % (self.rel, ntiid)
		return result

	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)

@interface.implementer(graph_interfaces.IUniqueAttributeAdapter)
@component.adapter(nti_interfaces.IContained,
				   graph_interfaces.IContainer,
				   graph_interfaces.IContained)
class _ContainedRelationshipUniqueAttributeAdpater(object):

	def __init__(self, obj, container, rel):
		self.obj = obj
		self.rel = rel
		self.container = container

	@property
	def key(self):
		return to_external_ntiid_oid(self.obj)

	@property
	def value(self):
		result = '%s,%s' % (self.rel, self.container.id)
		return result
	
	def __str__(self):
		return "(%s,%r)" % (self.key, self.value)

	def __repr__(self):
		return "%s(%s,%r)" % (self.__class__.__name__, self.key, self.value)
