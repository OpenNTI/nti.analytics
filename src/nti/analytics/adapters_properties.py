#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

import zope.intid
from zope import component
from zope import interface

from pyramid.traversal import find_interface

from nti.app.assessment import interfaces as app_asm_interfaces

from nti.assessment import interfaces as asm_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.contentsearch import interfaces as search_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.externalization import externalization

from nti.store import interfaces as store_interfaces

from . import common
from . import interfaces as graph_interfaces

def get_ntiid(obj):
	return getattr(obj, 'NTIID', getattr(obj, 'ntiid'))

def _set_intid(obj, ext):
	intids = component.getUtility(zope.intid.IIntIds)
	uid = intids.queryId(obj)
	if uid is not None:
		ext['intid'] = uid
	return ext

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(interface.Interface)
def _GenericPropertyAdpater(obj):
	result = {'createdTime':time.time()}
	result['lastModified'] = getattr(obj, 'lastModified', 0)
	_set_intid(obj, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.IEntity)
def _EntityPropertyAdpater(entity):
	result = {"username":entity.username, "creator":entity.username}
	result['createdTime'] = entity.createdTime
	names = user_interfaces.IFriendlyNamed(entity, None)
	alias = getattr(names, 'alias', None)
	name = getattr(names, 'realname', None)
	for key, value in (('alias', alias), ('name', name)):
		if value:
			result[key] = unicode(value)
	result['oid'] = externalization.to_external_ntiid_oid(entity)
	_set_intid(entity, result)
	return result

@component.adapter(nti_interfaces.ICommunity)
def _CommunityPropertyAdpater(community):
	result = _EntityPropertyAdpater(community)
	result['type'] = u'Community'
	return result

@component.adapter(nti_interfaces.IUser)
def _UserPropertyAdpater(user):
	result = _EntityPropertyAdpater(user)
	result['type'] = u'User'
	return result

@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
def _DFLPropertyAdpater(dfl):
	result = _EntityPropertyAdpater(dfl)
	result['type'] = u'DFL'
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.ICreated)
def _CreatedPropertyAdpater(created):
	result = {'type':created.__class__.__name__}
	_set_intid(created, result)
	result['oid'] = externalization.to_external_ntiid_oid(created)
	result['lastModified'] = getattr(created, 'lastModified', 0)
	result['createdTime'] = getattr(created, 'createdTime', None) or time.time()
	creator = getattr(created, 'creator', None)
	creator = getattr(creator, 'username', creator)
	if creator:
		result['creator'] = creator
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.IModeledContent)
def _ModeledContentPropertyAdpater(modeled):
	result = _CreatedPropertyAdpater(modeled)
	containerId = getattr(modeled, 'containerId', None)
	if containerId:
		result['containerId'] = containerId
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.ITitledContent)
def _TitledContentPropertyAdpater(content):
	result = _ModeledContentPropertyAdpater(content)
	result['title'] = unicode(content.title) or u''
	return result

_NotePropertyAdpater = _TitledContentPropertyAdpater
_HighlightPropertyAdpater = _ModeledContentPropertyAdpater
_RedactionPropertyAdpater = _ModeledContentPropertyAdpater

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(frm_interfaces.IBoard)
def _BoardPropertyAdpater(board):
	result = {'type':'Board'}
	result['title'] = unicode(board.title)
	result['createdTime'] = board.createdTime
	result['lastModified'] = getattr(board, 'lastModified', 0)
	result['oid'] = externalization.to_external_ntiid_oid(board)
	_set_intid(board, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(frm_interfaces.IForum)
def _ForumPropertyAdpater(forum):
	result = {'type':'Forum'}
	result['title'] = unicode(forum.title)
	result['createdTime'] = forum.createdTime
	result['lastModified'] = getattr(forum, 'lastModified', 0)
	result['oid'] = externalization.to_external_ntiid_oid(forum)
	_set_intid(forum, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(frm_interfaces.ITopic)
def _TopicPropertyAdpater(topic):
	result = {'type':'Topic'}
	creator = common.get_creator(topic)
	if creator is not None:
		result['creator'] = creator.username
	result['title'] = unicode(topic.title)
	result['ntiid'] = topic.NTIID
	result['createdTime'] = topic.createdTime
	result['lastModified'] = getattr(topic, 'lastModified', 0)
	result['oid'] = externalization.to_external_ntiid_oid(topic)
	result['forum'] = externalization.to_external_ntiid_oid(topic.__parent__)
	_set_intid(topic, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(frm_interfaces.IHeadlinePost)
def _HeadlinePostPropertyAdpater(post):
	return graph_interfaces.IPropertyAdapter(post.__parent__)

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(chat_interfaces.IMeeting)
def _MeetingPropertyAdpater(meeting):
	result = {'type':'Meeting'}
	creator = common.get_creator(meeting)
	if creator is not None:
		result['creator'] = creator.username
	result['roomId'] = meeting.RoomId
	result['moderated'] = meeting.Moderated
	result['createdTime'] = meeting.CreatedTime
	result['lastModified'] = getattr(meeting, 'lastModified', 0)
	result['oid'] = externalization.to_external_ntiid_oid(meeting)
	_set_intid(meeting, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(chat_interfaces.IMessageInfo)
def _MessageInfoPropertyAdpater(message):
	result = _ModeledContentPropertyAdpater(message)
	result['channel'] = message.channel
	result['status'] = message.Status
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
def _CommentPropertyAdpater(post):  # IPersonalBlogComment, IGeneralForumComment
	result = {'type':'Comment'}
	creator = common.get_creator(post)
	if creator is not None:
		result['creator'] = creator.username
	result['oid'] = externalization.to_external_ntiid_oid(post)
	result['topic'] = post.__parent__.NTIID
	result['createdTime'] = post.createdTime
	result['lastModified'] = getattr(post, 'lastModified', 0)
	_set_intid(post, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(lib_interfaces.IContentUnit)
def _ContentUnitPropertyAdpater(unit):
	result = {'type':'ContentUnit'}
	result['title'] = unit.title
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	result['oid'] = result['ntiid'] = unit.ntiid
	_set_intid(unit, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(graph_interfaces.IContainer)
def _ContainerPropertyAdpater(container):
	result = {'type':'Container'}
	result['oid'] = container.id
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	_set_intid(container, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(store_interfaces.IPurchaseAttempt)
def _PurchaseAttemptPropertyAdpater(pa):
	result = _CreatedPropertyAdpater(pa)
	items = {x.NTIID for x in pa.Order.Items}
	result['items'] = ','.join(items)
	result['state'] = pa.State
	if store_interfaces.IEnrollmentPurchaseAttempt.providedBy(pa):
		result['type'] = "Enrollment"
	elif store_interfaces.IInvitationPurchaseAttempt.providedBy(pa):
		result['type'] = "PurchaseInvitation"
	elif store_interfaces.IRedeemedPurchaseAttempt.providedBy(pa):
		result['type'] = "PurchaseRedeemed"
	else:
		result['type'] = "Purchase"
	return result

# IPersonalBlogComment, IGeneralForumComment
@interface.implementer(graph_interfaces.IPropertyAdapter)
def _CommentRelationshipPropertyAdpater(_from, _post, _rel):
	result = {'createdTime': _post.createdTime}
	result['lastModified'] = getattr(_post, 'lastModified', 0)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(asm_interfaces.IQuestionSet)
def _QuestionSetPropertyAdpater(obj):
	result = {'type':'QuestionSet'}
	result['ntiid'] = result['oid'] = get_ntiid(obj)
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	_set_intid(obj, result)
	return result
	
@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(asm_interfaces.IQuestion)
def _QuestionPropertyAdpater(obj):
	result = {'type':'Question'}
	result['ntiid'] = result['oid'] = get_ntiid(obj)
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	_set_intid(obj, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(asm_interfaces.IQAssignment)
def _AssignmentPropertyAdpater(obj):
	result = {'type':'Assignment'}
	result['ntiid'] = result['oid'] = get_ntiid(obj)
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	_set_intid(obj, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(app_asm_interfaces.IUsersCourseAssignmentHistoryItemFeedback)
def _AssignmentFeedbackPropertyAdpater(feedback):
	result = _ModeledContentPropertyAdpater(feedback)
	result['type'] = 'AssignmentFeedback'
	item = find_interface(feedback, app_asm_interfaces.IUsersCourseAssignmentHistoryItem)
	result['assignmentId'] = getattr(item, '__name__', None)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(asm_interfaces.IQAssessedPart)
def _QAssessedPartPropertyAdpater(obj):
	result = {'type':'AssessedPart'}
	result['assessedValue'] = obj.assessedValue
	result['createdTime'] = time.time()
	result['oid'] = externalization.to_external_ntiid_oid(obj)
	result['lastModified'] = getattr(obj, 'lastModified', None) or time.time()
	_set_intid(obj, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(asm_interfaces.IQAssessedQuestion)
def _QAssessedQuestionPropertyAdpater(obj):
	result = {'type':'AssessedQuestion'}
	result['createdTime'] = obj.createdTime
	result['questionId'] = obj.questionId
	result['oid'] = externalization.to_external_ntiid_oid(obj)
	result['lastModified'] = getattr(obj, 'lastModified', None) or time.time()
	_set_intid(obj, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(asm_interfaces.IQAssessedQuestionSet)
def _QAssessedQuestionSetPropertyAdpater(obj):
	result = {'type':'AssessedQuestionSet'}
	creator = common.get_creator(obj)
	if creator is not None:
		result['creator'] = creator.username
	result['createdTime'] = obj.createdTime
	result['questionSetId'] = obj.questionSetId
	result['oid'] = externalization.to_external_ntiid_oid(obj)
	result['lastModified'] = getattr(obj, 'lastModified', None) or time.time()
	_set_intid(obj, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(search_interfaces.ISearchQuery)
def _SearchQueryPropertyAdpater(obj):
	result = {'type':'SearchQuery'}
	result['term'] = obj.term.lower()
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	result['IsPhraseSearch'] = obj.IsPhraseSearch
	result['IsPrefixSearch'] = obj.IsPrefixSearch
	_set_intid(obj, result)
	return result

def _question_stats(question):
	total = incorrect = correct = partial = 0
	for part in question.parts:
		total += 1
		if part.assessedValue <= 0.01:
			incorrect += 1
		elif part.assessedValue >= 0.99:
			correct += 1
		else:
			partial += 1
	return (total == correct, total == incorrect, partial > 0)

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.IUser, asm_interfaces.IQAssessedQuestion,
				   graph_interfaces.ITakeAssessment)
def _AssessedQuestionRelationshipPropertyAdpater(user, question, rel):
	result = {'creator' : user.username}
	result['createdTime'] = question.createdTime
	result['oid'] = externalization.to_external_ntiid_oid(question)
	result['questionId'] = question.questionId
	is_correct, is_incorrect, partial = _question_stats(question)
	result['correct'] = is_correct
	result['incorrect'] = is_incorrect
	result['partial'] = partial
	result['lastModified'] = getattr(question, 'lastModified', None) or time.time()
	_set_intid(question, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.IUser, asm_interfaces.IQAssessedQuestionSet,
				   graph_interfaces.ITakeAssessment)
def _AssessedQuestionSetRelationshipPropertyAdpater(user, questionSet, rel):
	result = {'creator' : user.username}
	result['createdTime'] = questionSet.createdTime
	result['oid'] = externalization.to_external_ntiid_oid(questionSet)
	result['questionSetId'] = questionSet.questionSetId
	correct = incorrect = 0
	questions = questionSet.questions
	for question in questions:
		is_correct, is_incorrect, _ = _question_stats(question)
		if is_correct:
			correct += 1
		elif is_incorrect:
			incorrect += 1
	result['correct'] = correct
	result['incorrect'] = incorrect
	result['lastModified'] = getattr(questionSet, 'lastModified', None) or time.time()
	_set_intid(questionSet, result)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.IUser, asm_interfaces.IQAssignment,
				   graph_interfaces.ITakeAssessment)
def _AssignmentRelationshipPropertyAdpater(user, asm, rel):
	result = {'creator' : user.username}
	result['createdTime'] = time.time()
	result['lastModified'] = time.time()
	result['assignmentId'] = result['oid'] = get_ntiid(asm)
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
def _CreatedTimePropertyAdpater(_from, _to, _rel):
	result = {'createdTime':time.time()}
	result['lastModified'] = time.time()
	return result

@interface.implementer(graph_interfaces.IPropertyAdapter)
def _EntityObjectRelationshipPropertyAdpater(entity, obj, rel_type):
	result = {'createdTime':getattr(obj, 'createdTime', time.time())}
	result['creator'] = entity.username
	result['oid'] = externalization.to_external_ntiid_oid(obj)
	result['lastModified'] = getattr(obj, 'lastModified', None) or time.time()
	_set_intid(obj, result)
	return result

_LikeRelationshipPropertyAdpater = _EntityObjectRelationshipPropertyAdpater
_RateRelationshipPropertyAdpater = _EntityObjectRelationshipPropertyAdpater
_RepliedRelationshipPropertyAdpater = _EntityObjectRelationshipPropertyAdpater
_FlaggedRelationshipPropertyAdpater = _EntityObjectRelationshipPropertyAdpater
_AuthorshipRelationshipPropertyAdpater = _EntityObjectRelationshipPropertyAdpater

_FollowRelationshipPropertyAdpater = _CreatedTimePropertyAdpater

@interface.implementer(graph_interfaces.IPropertyAdapter)
@component.adapter(nti_interfaces.IUser, search_interfaces.ISearchResults,
				   graph_interfaces.ISearch)
def _SearchRelationshipPropertyAdpater(user, results, rel):
	result = {'createdTime': time.time()}
	result['creator'] = user.username
	result['lastModified'] = time.time()
	# query properties
	if results.Query.location:
		result['location'] = results.Query.location

	searchOn = sorted(results.Query.searchOn or ())
	if searchOn:
		result['searchOn'] = ','.join(searchOn)
		
	creator = results.Query.creator
	if creator:
		result['searchCreator'] = creator

	for name in ('creationTime', 'modificationTime'):
		value = getattr(results.Query, name, None)
		if value is not None:
			result[name] = value

	# meta data properties
	result['searchTime'] = results.HitMetaData.SearchTime
	result['totalHitCount'] = results.HitMetaData.TotalHitCount
	items = results.HitMetaData.ContainerCount.items()  # top 5 containers
	for x, y in sorted(items, key=lambda x: x[1], reverse=True)[:5]:
		result[x] = y
	return result
