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

class IObjectProcessor(interface.Interface):

	def init( obj ):
		"""
		Does analytic processing for the given object.
		"""

class IResourceEvent(interface.Interface):
	"""
	Describes a resource viewing event.
	"""

	timestamp = Number(title=u"The timestamp when this event occurred.",
						default=0.0)

	user = ValidTextLine(title='User who created the event')

	# We could grab this via the resource_id
	course = ValidTextLine(title='Course id')

	# TODO This is really undefined...
	context_path = ValidTextLine(title='Context path',
								description='Slash separated values describing where the event occurred.')

	resource_id = ValidTextLine(title="The resource ntiid.")

	time_length = Number(title=u"The time length of the event, in seconds",
						default=0)

class IVideoEvent(IResourceEvent):
	"""
	Describes a video event.
	"""
	# TODO Should we have separate video interfaces? WATCH OR SKIP
	event_type = ValidTextLine(title='The type of video event {WATCH, SKIP}')

	video_start_time = Number(title=u"The point in the video that starts playing, in seconds.",
							default=0)

	video_end_time = Number(title=u"The point at which the video stops playing, in seconds.",
							default=0)

	with_transcript = Bool(title=u"Whether the video was viewed with a transcript or not.")

class IBatchResourceEvents( IIterable ):
	events = TypedIterable(
		title="The events in this batch",
		value_type=Object( IResourceEvent ) )
