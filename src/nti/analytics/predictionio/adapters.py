#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contentlibrary.interfaces import IContentUnit

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.externalization.externalization import to_external_ntiid_oid

from .interfaces import IOID
from .interfaces import IType
from .interfaces import IProperties

def get_tag_types(item):
	result = []
	for name in ('tags', 'AutoTags'):
		tpl = getattr(item, name, None) or ()
		result.extend(t.lower() for  t in tpl)
	return result

@interface.implementer(IProperties)
@component.adapter(interface.Interface)
def _GenericPropertyAdpater(item):
	return {'Class': item.__class__.__name__}

@interface.implementer(IProperties)
@component.adapter(IUser)
def _UserPropertyAdpater(user):
	profile = IFriendlyNamed(user)
	result = {'name':profile.realname, 'alias':profile.alias}
	return result

@interface.implementer(IProperties)
@component.adapter(INote)
def _NotePropertyAdpater(note):
	result = {'title':note.title,
			  'tags': '%s' % get_tag_types(note)}
	return result

@interface.implementer(IProperties)
@component.adapter(IContentUnit)
def _ContentUnitPropertyAdpater(item):
	result = {'title':item.title}
	return result

@interface.implementer(IType)
@component.adapter(interface.Interface)
def _GenericTypesAdpater(item):
	name = item.__class__.__name__
	return name.lower(),

@interface.implementer(IType)
@component.adapter(IModeledContent)
def _ModeledTypesAdpater(item):
	name = item.__class__.__name__
	result = name.lower()
	return result

@interface.implementer(IType)
def _CommentTypesAdpater(item):
	result = 'comment'
	return result

@interface.implementer(IType)
@component.adapter(ITopic)
def _TopicTypesAdpater(item):
	result = 'topic'
	return result

@interface.implementer(IType)
@component.adapter(IContentUnit)
def _ContentUnitTypesAdpater(item):
	result = 'contentunit'
	return result

@interface.implementer(IOID)
@component.adapter(interface.Interface)
def _GenericOIDAdpater(item):
	result = to_external_ntiid_oid(item)
	return result

@interface.implementer(IOID)
@component.adapter(IContentUnit)
def _ContentUnitOIDAdpater(item):
	result = item.ntiid
	return result

@interface.implementer(IOID)
@component.adapter(IUser)
def _UserOIDAdpater(user):
	result = user.username
	return result
