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
import zope.exceptions.log

from nti.async.utils.processor import Processor

from nti.analytics import FAIL_QUEUE
from nti.analytics.interfaces import IObjectProcessor

class Constructor(Processor):

	def set_log_formatter(self, args):
		super(Constructor, self).set_log_formatter(args)
		if args.verbose:
			for _, module in component.getUtilitiesFor(IObjectProcessor):
				module.logger.setLevel(logging.DEBUG)

	def process_args(self, args):
		setattr(args, 'library', True)  # load library
		setattr(args, 'queue_names', [FAIL_QUEUE])
		super(Constructor, self).process_args(args)

def main():
 	return Constructor()()

if __name__ == '__main__':
	main()
