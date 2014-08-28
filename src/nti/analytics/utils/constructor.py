#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import logging

from zope import component

from nti.async.utils.processor import Processor

from nti.analytics import FAIL_QUEUE
from nti.analytics import QUEUE_NAMES
from nti.analytics.interfaces import IObjectProcessor

from nti.zodb import activitylog
# Runtime: bin/nti_analytics_constructor -v --site platform.ou.edu

class Constructor(Processor):

	def set_log_formatter(self, args):
		super(Constructor, self).set_log_formatter(args)
		if args.verbose:
			for _, module in component.getUtilitiesFor(IObjectProcessor):
				module.logger.setLevel(logging.DEBUG)
		activitylog.logger.setLevel( logging.DEBUG )

	def process_args(self, args):
		setattr(args, 'library', True)  # load library
		setattr(args, 'fail_queue', FAIL_QUEUE)
		setattr(args, 'queue_names', QUEUE_NAMES)
		setattr(args, 'redis', True)
		super(Constructor, self).process_args(args)

def main():
	return Constructor()()

if __name__ == '__main__':
	main()
