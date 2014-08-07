#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Bool
from nti.schema.field import DecodingValidTextLine as ValidTextLine
from nti.schema.field import IndexedIterable as TypedIterable

from dolmen.builtins.interfaces import IIterable

class IAnalyticsQueueFactory(interface.Interface):
	"""
	A factory for analytics processing queues.
	"""

class IObjectProcessor(interface.Interface):

	def init( obj ):
		"""
		Does analytic processing for the given object.
		"""
class ICourseEvent(interface.Interface):
	"""
	A course event.
	"""
	timestamp = Number(title=u"The timestamp when this event occurred.",
						default=0.0)

	user = ValidTextLine(title='User who created the event')

	course = ValidTextLine(title='Course ntiid')

	time_length = Number(title=u"The time length of the event, in seconds",
						default=0)

class IResourceEvent(ICourseEvent):
	"""
	Describes a resource viewing event.
	"""
	# TODO This is really undefined...
	context_path = ValidTextLine(title='Context path',
								description='Slash separated values describing where the event occurred.')

	resource_id = ValidTextLine(title="The resource ntiid.")



class IVideoEvent(IResourceEvent):
	"""
	Describes a video event.
	"""
	event_type = ValidTextLine(title='The type of video event {WATCH, SKIP}')

	video_start_time = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	video_end_time = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0)

	with_transcript = Bool(title=u"Whether the video was viewed with a transcript or not.")

class ICourseCatalogViewEvent(ICourseEvent):
	"""
	Describes a course catalog viewing event.
	"""

class IBatchResourceEvents( IIterable ):
	events = TypedIterable(
		title="The events in this batch",
		value_type=Object( ICourseEvent ) )
