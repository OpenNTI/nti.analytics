#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import itertools

from zope import component
from zope import interface

from nti.app.assessment import interfaces as app_asm_interfaces

from nti.assessment import interfaces as asm_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.contentsearch import interfaces as search_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.store import interfaces as store_interfaces

from . import interfaces as graph_interfaces

#### labels

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(interface.Interface)
def _GenericLabelAdpater(obj):
	return ()

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(nti_interfaces.IEntity)
def _EntityLabelAdpater(entity):
	return (entity.__class__.__name__.lower(),)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(nti_interfaces.IUser)
def _UserLabelAdpater(entity):
	return ('user',)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
def _DFLLabelAdpater(obj):
	return ('dfl',)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(nti_interfaces.IModeledContent)
def _ModeledContentLabelAdpater(modeled):
	return (modeled.__class__.__name__.lower(),)

@component.adapter(nti_interfaces.INote)
def _NoteLabelAdpater(note):
	chained = itertools.chain(['note'], note.tags or ())
	result = {w.lower() for w in chained}
	return tuple(sorted(result))

@interface.implementer(graph_interfaces.ILabelAdapter)
def _CommentLabelAdpater(obj):
	result = ('comment',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(frm_interfaces.IForum)
def _ForumLabelAdpater(modeled):
	return ("forum",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(frm_interfaces.ITopic)
def _TopicLabelAdpater(topic):
	htags = getattr(topic.headline, 'tags', ())
	chained = itertools.chain(['topic'], topic.tags or (), htags or ())
	result = {w.lower() for w in chained}
	result = tuple(sorted(result))
	return result
	
@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(frm_interfaces.IBoard)
def _BoardLabelAdpater(modeled):
	return ("board",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(frm_interfaces.IHeadlinePost)
def _HeadlinePostLabelAdpater(post):
	return graph_interfaces.ILabelAdapter(post.__parent__)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(lib_interfaces.IContentUnit)
def _ContentUnitLabelAdpater(topic):
	return ("contentunit",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(asm_interfaces.IQuestionSet)
def _QuestionSetLabelAdpater(obj):
	result = ('questionset',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(asm_interfaces.IQuestion)
def _QuestionLabelAdpater(question):
	result = ('question',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(asm_interfaces.IQAssignment)
def _AssignmentLabelAdpater(question):
	result = ('assignment',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(app_asm_interfaces.IUsersCourseAssignmentHistoryItemFeedback)
def _AssignmentFeedbackLabelAdpater(modeled):
	return ("assignmentFeedback",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(asm_interfaces.IQAssessedPart)
def _QAssessedPartLabelAdpater(obj):
	return ("assessedPart",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(asm_interfaces.IQAssessedQuestion)
def _QAssessedQuestionLabelAdpater(obj):
	return ("assessedQuestion",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(asm_interfaces.IQAssessedQuestionSet)
def _QAssessedQuestionSetLabelAdpater(obj):
	return ("assessedQuestionSet",)

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(chat_interfaces.IMeeting)
def _MeetingLabelAdpater(meeting):
	result = ('meeting',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(chat_interfaces.IMessageInfo)
def _MessageInfoLabelAdpater(message):
	result = ('message',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(search_interfaces.ISearchQuery)
def _SearchQueryLabelAdpater(query):
	result = ('searchquery',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(graph_interfaces.IContainer)
def _ContainerLabelAdpater(container):
	result = ('container',)
	return result

@interface.implementer(graph_interfaces.ILabelAdapter)
@component.adapter(store_interfaces.IPurchaseAttempt)
def _PurchaseAttemptLabelAdpater(pa):
	result = ("purchase",)
	if store_interfaces.IEnrollmentAttempt.providedBy(pa):
		result = ("enrollment",)
	elif store_interfaces.IInvitationPurchaseAttempt.providedBy(pa):
		result = ("purchaseInvitation",)
	elif store_interfaces.IRedeemedPurchaseAttempt.providedBy(pa):
		result = ("purchaseRedeemed",)
	return result

