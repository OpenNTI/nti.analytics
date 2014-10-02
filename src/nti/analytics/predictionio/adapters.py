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

from .interfaces import ITypes
from .interfaces import IProperties

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
	result = {'title':note.title}
	return result

@interface.implementer(IProperties)
@component.adapter(IContentUnit)
def _ContentUnitPropertyAdpater(item):
	result = {'title':item.title}
	return result

@interface.implementer(ITypes)
@component.adapter(interface.Interface)
def _GenericTypesAdpater(item):
	name = item.__class__.__name__
	return (name.lower(),)

def get_tag_types(item):
	result =()
	for name in ('tags', 'AutoTags'):
		tpl = getattr(item, name, None) or ()
		result += tuple((t.lower() for  t in tpl))
	return result

@interface.implementer(ITypes)
@component.adapter(IModeledContent)
def _ModeledTypesAdpater(item):
	name = item.__class__.__name__
	result = (name.lower(),) + get_tag_types(item)
	return result

@interface.implementer(ITypes)
def _CommentTypesAdpater(item):
	result = ('comment',) + get_tag_types(item)
	return result

@interface.implementer(ITypes)
@component.adapter(ITopic)
def _TopicTypesAdpater(item):
	result = ('topic',) + get_tag_types(item)
	return result

@interface.implementer(ITypes)
@component.adapter(IContentUnit)
def _ContentUnitTypesAdpater(item):
	result = ('contentunit',)
	return result
