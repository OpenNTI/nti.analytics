#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.analytics.adapters import DefaultProgress

def get_progress_for_resource_views( resource_ntiid, resource_views ):
	"""Simplistic; looking at a resource constitutes progress."""
	result = None
	if resource_views:
		result = DefaultProgress( resource_ntiid, 1, 1, True )
	return result

def get_progress_for_video_views( resource_ntiid, video_events  ):
	"""
	Simplistic; looking at a resource constitutes progress.

	#TODO We want to do more, but it seems
	unlikely that we can do better unless we know the max length of the video.
	"""
	result = None
	if video_events:
		result = DefaultProgress( resource_ntiid, 1, 1, True )
	return result
