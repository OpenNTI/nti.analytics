#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from zope.container.interfaces import IContained

from zope.interface.interfaces import ObjectEvent, IObjectEvent

from dolmen.builtins import IString
from dolmen.builtins import INumeric

from nti.common.property import alias

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import	ICourseCatalogEntry

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IUser
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import ValidTextLine

class IObjectRecordedEvent(IObjectEvent):
	user = Object(IUser, title="user that viewed object")
	timestamp = Number(title=u"The timestamp when this event occurred",
						default=0.0,
						required=False)
	session = interface.Attribute("analytics session")

class IObjectViewedRecordedEvent(IObjectRecordedEvent):
	duration = Number(title="Time length duration", required=False, default=0)
	context_path = List(title='Context path',
						description='List of ntiid locations describing where the event occurred.',
						min_length=0,
						default=None,
						required=False,
						value_type=ValidTextLine(title='The ntiid context segment'))

class INoteViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(INote, title="note viewed", required=True)
	context = Object(ICourseInstance, title="root context", required=False)

class ITopicViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(ITopic, title="topic viewed", required=True)
	context = Variant((Object(IString, title="the context id"),
					   Object(INumeric, title="the context id"),
					   Object(ICourseInstance, title="the context course")),
					 title="context object", required=False)

class ICatalogViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Variant((Object(ICourseInstance, title="the course"),
					  Object(ICourseCatalogEntry, title="the course entry")),
					 title="course/catalog viewed", required=True)

class IBlogViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IContained, title="blog viewed", required=True)

class IResourceViewedRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IString, title="resourced viewed", required=True)
	context = Variant((Object(IString, title="the context id"),
					   Object(INumeric, title="the context id"),
					   Object(ICourseInstance, title="the context course")),
					 title="context object", required=False)

class IVideoRecordedEvent(IObjectViewedRecordedEvent):
	object = Object(IString, title="video id", required=True)
	video_start_time = Number(title="Start time (secs)", required=False, default=0)
	video_end_time = Number(title="End time (secs)", required=False, default=0)
	with_transcript = Bool(title="Viewed with a trascript", required=False, default=False)
	context = Variant((Object(IString, title="the context id"),
					   Object(INumeric, title="the context id"),
					   Object(ICourseInstance, title="the context course")),
					 title="context object", required=False)

class IVideoWatchRecordedEvent(IVideoRecordedEvent):
	pass

class IVideoSkipRecordedEvent(IVideoRecordedEvent):
	pass

class IProfileViewedRecordedEvent(IObjectViewedRecordedEvent):
	profile = ValidTextLine(title="The profile entity username.", required=True)

class IProfileActivityViewedRecordedEvent(IProfileViewedRecordedEvent):
	pass

class IProfileMembershipViewedRecordedEvent(IProfileViewedRecordedEvent):
	pass

@interface.implementer(IObjectRecordedEvent)
class ObjectRecordedEvent(ObjectEvent):

	sessionId = alias('session')

	def __init__(self, user, obj, timestamp=None, session=None):
		super(ObjectRecordedEvent, self).__init__(obj)
		self.user = user
		self.session = session
		self.timestamp = timestamp or 0.0

@interface.implementer(IObjectRecordedEvent)
class ObjectViewedRecordedEvent(ObjectRecordedEvent):

	def __init__(self, user, obj, timestamp=None, session=None, duration=None, context_path=None):
		super(ObjectViewedRecordedEvent, self).__init__(user, obj, 
														session=session,
														timestamp=timestamp)
		self.duration = duration
		self.context_path = context_path

@interface.implementer(INoteViewedRecordedEvent)
class NoteViewedRecordedEvent(ObjectViewedRecordedEvent):

	note = alias('object')

	def __init__(self, user, note, context=None, timestamp=None, session=None, duration=None, context_path=None):
		super(NoteViewedRecordedEvent, self).__init__(user, note,
													  session=session,
													  duration=duration,
													  timestamp=timestamp,
													  context_path=context_path)
		self.context = context

@interface.implementer(ITopicViewedRecordedEvent)
class TopicViewedRecordedEvent(ObjectViewedRecordedEvent):

	topic = alias('object')

	def __init__(self, user, topic, context=None, timestamp=None, session=None, duration=None, context_path=None):
		super(TopicViewedRecordedEvent, self).__init__(user, topic,
													   session=session,
													   duration=duration,
													   timestamp=timestamp,
													   context_path=context_path)
		self.context = context

@interface.implementer(IBlogViewedRecordedEvent)
class BlogViewedRecordedEvent(ObjectViewedRecordedEvent):

	blog = alias('object')

	def __init__(self, user, blog, timestamp=None, session=None, duration=None, context_path=None):
		super(BlogViewedRecordedEvent, self).__init__(user, blog,
													  session=session,
													  duration=duration,
													  timestamp=timestamp,
													  context_path=context_path)

@interface.implementer(ICatalogViewedRecordedEvent)
class CatalogViewedRecordedEvent(ObjectViewedRecordedEvent):

	catalog = course = alias('object')

	def __init__(self, user, context, timestamp=None, session=None, duration=None, context_path=None):
		super(CatalogViewedRecordedEvent, self).__init__(user, context, 
														 session=session,
													  	 duration=duration,
													  	 timestamp=timestamp,
													  	 context_path=context_path)

@interface.implementer(IResourceViewedRecordedEvent)
class ResourceViewedRecordedEvent(ObjectViewedRecordedEvent):

	resource = alias('object')

	def __init__(self, user, resource, context=None, timestamp=None, session=None, duration=None, context_path=None):
		super(ResourceViewedRecordedEvent, self).__init__(user, resource, 
														  session=session,
													  	  duration=duration,
													  	  timestamp=timestamp,
													  	  context_path=context_path)
		self.context = context

@interface.implementer(IVideoRecordedEvent)
class VideoRecordedEvent(ObjectViewedRecordedEvent):

	resource = alias('object')
	time_length = alias('duration')

	def __init__(self, user, video, context=None, timestamp=None, session=None,
				 context_path=None, duration=0, video_start_time=0,
				 video_end_time=0, with_transcript=False):
		super(VideoRecordedEvent, self).__init__(user, video, timestamp, session, context_path)
		self.context = context
		self.duration = duration
		self.video_end_time = video_end_time
		self.with_transcript = with_transcript
		self.video_start_time = video_start_time

@interface.implementer(IVideoWatchRecordedEvent)
class VideoWatchRecordedEvent(VideoRecordedEvent):
	pass

@interface.implementer(IVideoSkipRecordedEvent)
class VideoSkipRecordedEvent(VideoRecordedEvent):
	pass

@interface.implementer(IProfileViewedRecordedEvent)
class ProfileViewedRecordedEvent(ObjectViewedRecordedEvent):

	profile = alias('object')

	def __init__(self, user, profile, timestamp=None, session=None, context_path=None):
		super(ProfileViewedRecordedEvent, self).__init__(user, profile, timestamp, session, context_path)

@interface.implementer(IProfileActivityViewedRecordedEvent)
class ProfileActivityViewedRecordedEvent(ProfileViewedRecordedEvent):
	pass

@interface.implementer(IProfileMembershipViewedRecordedEvent)
class ProfileMembershipViewedRecordedEvent(ProfileViewedRecordedEvent):
	pass
