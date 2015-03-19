#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import numbers

from zope import component
from zope import interface

from dolmen.builtins.interfaces import IString, INumeric

from nti.contentlibrary.interfaces import IContentUnit

from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.presentation.interfaces import INTIIDIdentifiable

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IModeledContent

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.externalization.externalization import to_external_ntiid_oid

from nti.ntiids.ntiids import get_type
from nti.ntiids.ntiids import is_valid_ntiid_string

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
@component.adapter(IString)
def _StringPropertyAdpater(item):
	return {}

@interface.implementer(IProperties)
@component.adapter(interface.Interface)
def _GenericPropertyAdpater(item):
	if isinstance(item, six.string_types):
		result = _StringPropertyAdpater(item)
	else:
		result = {'Class': item.__class__.__name__}
	return result

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
@component.adapter(IString)
def _StringTypeAdpater(item):
	if is_valid_ntiid_string(item):
		result = get_type(item)
	else:
		result = item
	return result

@interface.implementer(IType)
@component.adapter(interface.Interface)
def _GenericTypeAdpater(item):
	if isinstance(item, six.string_types):
		result = _StringTypeAdpater(item)
	else:
		result = item.__class__.__name__
		result = result.lower()
	return result

@interface.implementer(IType)
@component.adapter(IModeledContent)
def _ModeledTypeAdpater(item):
	name = item.__class__.__name__
	result = name.lower()
	return result

@interface.implementer(IType)
def _CommentTypeAdpater(item):
	result = 'comment'
	return result

@interface.implementer(IType)
@component.adapter(ITopic)
def _TopicTypeAdpater(item):
	result = 'topic'
	return result

@interface.implementer(IType)
@component.adapter(IContentUnit)
def _ContentUnitTypeAdpater(item):
	result = 'contentunit'
	return result

@interface.implementer(IOID)
@component.adapter(IString)
def _StringOIDAdpater(value):
	return value

@interface.implementer(IOID)
@component.adapter(INumeric)
def _NumericOIDAdpater(value):
	return value

@interface.implementer(IOID)
@component.adapter(interface.Interface)
def _GenericOIDAdpater(item):
	if isinstance(item, six.string_types):
		result = _StringOIDAdpater(item)
	elif isinstance(item, numbers.Number):
		result = _NumericOIDAdpater(item)
	else:
		result = to_external_ntiid_oid(item)
	return result

@interface.implementer(IOID)
@component.adapter(IContentUnit)
def _ContentUnitOIDAdpater(item):
	result = item.ntiid
	return result

@interface.implementer(IOID)
@component.adapter(ICourseCatalogEntry)
def _CourseCatalogEntryOIDAdpater(item):
	result = item.ntiid
	return result

@interface.implementer(IOID)
@component.adapter(IUser)
def _UserOIDAdpater(user):
	result = user.username
	return result

@interface.implementer(IOID)
@component.adapter(INTIIDIdentifiable)
def _NTIIDIdentifiableOIDAdpater(item):
	result = item.ntiid
	return result
