#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import logging
import argparse

from zope import component

from nti.async.utils.processor import Processor

from nti.analytics import QUEUE_NAMES
from nti.analytics import interfaces as analytic_interfaces


# Example command lines
# Migration: bin/nti_analytics_constructor -v --no_sleep --site platform.ou.edu
# Runtime: bin/nti_analytics_constructor -v --site platform.ou.edu

class Constructor(Processor):

	def set_log_formatter(self, args):
		super(Constructor, self).set_log_formatter(args)
		if args.verbose:
			for _, module in component.getUtilitiesFor(analytic_interfaces.IObjectProcessor):
				module.logger.setLevel(logging.DEBUG)

	def process_args(self, args):
		setattr(args, 'library', True)  # load library
		setattr(args, 'queue_names', QUEUE_NAMES)
		super(Constructor, self).process_args(args)

def main():
# 	import cProfile, pstats
# 	pr = cProfile.Profile()
# 	pr.enable()
# 	result = None
# 	try:
# 		result = Constructor()()
# 	finally:
# 		pr.disable()
# 		with open( '/Users/jzuech/analytics_profiling_orm.txt', 'w+' ) as f:
# 			pstats.Stats( pr, stream=f ).print_stats()
# 	return result
 	return Constructor()()

if __name__ == '__main__':
	main()
