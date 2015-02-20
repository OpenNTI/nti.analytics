#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageLibrary

from .utils import create_user_event

from . import VIEW_API

def get_content_unit(unit):
	if not IContentUnit.providedBy(unit):
		library = component.queryUtility(IContentPackageLibrary)
		paths = library.pathToNTIID(str(unit)) if library else ()
		result = paths[-1] if paths else None
	else:
		result = unit
	return result

def record_content_view(user, unit, params=None, request=None):
	unit = get_content_unit(unit)
	return create_user_event(event=VIEW_API, 
					  		 user=user,
					  		 obj=unit,
					  		 params=params)
