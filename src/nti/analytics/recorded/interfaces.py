#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.interface.interfaces import ObjectEvent, IObjectEvent

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IUser

from nti.utils.property import alias

from nti.schema.field import Object

class IObjectViewedRecordedEvent(IObjectEvent):
	user = Object(IUser, title="user that viewed object")

@interface.implementer(IObjectViewedRecordedEvent)
class ObjectViewedRecordedEvent(ObjectEvent):

	def __init__(self, user, obj):
		super(ObjectViewedRecordedEvent, self).__init__(obj)
		self.user = user
		
class INoteViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(INote, title="note viewed", required=True)
	course = Object(ICourseInstance, title="course", required=False)
	session = interface.Attribute("user session")

@interface.implementer(INoteViewedRecordedEvent)
class NoteViewedRecordedEvent(object):

	note = alias('object')
	
	def __init__(self, user, note, course=None, session=None):
		super(NoteViewedRecordedEvent, self).__init__(user, note)
		self.course = course
		self.session = session