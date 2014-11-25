#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.analytics.interfaces import IProgress

from nti.externalization.representation import WithRepr

@interface.implementer( IProgress )
@WithRepr
class DefaultProgress( object ):

	def __init__(self, progress_id, progress, max_progress, has_progress=False, last_modified=None ):
		self.progress_id = progress_id
		self.AbsoluteProgress = progress
		self.MaxPossibleProgress = max_progress
		self.HasProgress = has_progress
		self.last_modified = last_modified

def get_progress_for_resource_views( resource_ntiid, resource_views ):
	"""Simplistic; looking at a resource constitutes progress."""
	result = None
	if resource_views:
		result = DefaultProgress( resource_ntiid, 1, 1, True )
	return result

def get_progress_for_video_views( resource_ntiid, video_events  ):
	"""
	Simplistic; looking at a resource constitutes progress.
	"""
	result = None
	video_events = list( video_events )

	if video_events:
		# It may be enough to grab the first MaxDuration we find.  max
		# time may be null.
		max_time = max( (x.MaxDuration for x in video_events) )
		total_time = sum( (x.time_length for x in video_events) )
		result = DefaultProgress( resource_ntiid, total_time, max_time, True )
	return result
