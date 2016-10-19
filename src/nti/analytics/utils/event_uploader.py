#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Take malformed analytic event logs and push them into
our db.

Example log line:

2015-10-15 14:21:39,443 WARNI [nti.app.analytics.views][140480088675984:16729]
[/dataserver2/analytics/batch_events:bill.brasky@gmail.com] Malformed events
received (event={u'user': u'bill.brasky@gmail.com', u'type': u'resource-viewed',
u'RootContextID': u'tag:nextthought.com,2011-10:system-OID-0x010fad90:5573657273:jtu73uqRNU2',
u'MimeType': u'application/vnd.nextthought.analytics.resourceevent', u'context_path':
[u'tag:nextthought.com,2011-10:system-OID-0x010fad90:5573657273:jtu73uqRNU2',
u'tag:nextthought.com,2011-10:OC-HTML-Oklahoma_Christian_University_CMSC_1313_F_2015_Software_Engineering_I.lec:lesson_12_inclass'],
u'ResourceId': u'tag:nextthought.com,2011-10:OC-RelatedWorkRef-Oklahoma_Christian_University_CMSC_1313_F_2015_Software_Engineering_I.relatedworkref.relwk:12_2_lecture_presentation',
u'timestamp': 1444936880.005}) (resource_id)

This script will probably not need to be used again, but if so,
we could improve this by using transactional savepoints and
being able to accurately log how many events are loaded (e.g. dupes).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
import ast
import argparse

from zope.schema.interfaces import ValidationError

from nti.dataserver.users import User

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site
from nti.dataserver.utils.base_script import create_context

from nti.analytics.sessions import get_user_sessions

from nti.analytics import resource_views

from nti.analytics.common import timestamp_type
from nti.analytics.common import process_event

from nti.analytics.resource_views import UnrecoverableAnalyticsError

from nti.externalization import internalization

def _process_event_immediately(*args, **kwargs):
	"""
	Monkey patch process_event in order to execute jobs immediately.
	"""
	try:
		process_event(immediate=True, *args, **kwargs)
	except (ValueError, UnrecoverableAnalyticsError) as e:
		logger.error(e)

def _get_session_for_user_and_timestamp(event):
	"""
	Monkey patch get_nti_session_id to return sessions for a given
	timestamp.
	"""
	user = User.get_user(event.user)
	timestamp = event.timestamp
	timestamp = timestamp_type(timestamp)
	sessions = get_user_sessions(user, for_timestamp=timestamp)
	if sessions:
		return sessions[0].SessionID

resource_views.get_nti_session_id = _get_session_for_user_and_timestamp
resource_views.process_event = _process_event_immediately

EVENT_PATTERN = re.compile('.*event=({.*})')
USER_PATTERN = re.compile('batch_events:(.*?)]')

def _parse_log_line(line):
	"""
	Return the event and user from the log line.
	"""
	__traceback_info__ = line
	try:
		val = EVENT_PATTERN.search(line).group(1)
		user = USER_PATTERN.search(line).group(1)
	except AttributeError:
		logger.info('Line is not an event (%s)', line)
	else:
		obj = ast.literal_eval(val)
		return obj, user

BATCH_SIZE = 5000

def _load_events(events):
	if events:
		return resource_views.handle_events(events)
	return 0

def _process_batch_events(events):
	"""
	Process the events, returning a tuple of events queued and malformed events.
	"""
	batch_events = []
	malformed_count = missing_user_count = 0

	for event in events:
		factory = internalization.find_factory_for(event)
		new_event = factory()
		try:
			internalization.update_from_external_object(new_event, event)
			if not new_event.user:
				logger.warn('No user for event (%s)', new_event)
				missing_user_count += 1
				continue
			if not User.get_user(new_event.user):
				missing_user_count += 1
			batch_events.append(new_event)
		except ValidationError:
			malformed_count += 1

	event_count = _load_events(batch_events)
	return event_count, malformed_count, missing_user_count

def _process_args(site, file_name):
	if site:
		set_site(site)
	logger.info("Loading analytics events from file '%s' into site '%s'",
				file_name, site)
	processed_count = loaded_count = malformed_count = missing_user_count = 0
	events = []

	with open(file_name, 'r') as f:
		for line in f.readlines():
			parsed_objs = _parse_log_line(line)
			if parsed_objs is None:
				continue

			event, user = parsed_objs

			if 'user' not in event:
				event['user'] = user
			events.append(event)
			processed_count += 1

			if processed_count % BATCH_SIZE == 0:
				loaded, malformed, missing_user = _process_batch_events(events)
				loaded_count += loaded
				malformed_count += malformed
				missing_user_count += missing_user
				events = []  # Reset
				logger.info('Processed %s events...', processed_count)

	loaded, malformed, missing_user = _process_batch_events(events)
	loaded_count += loaded
	malformed_count += malformed
	missing_user_count += missing_user

	logger.info('Finished loading events (processed=%s) (loaded=%s) (malformed=%s) (missing_users=%s)',
				processed_count, loaded_count, malformed_count, missing_user_count)


def main():
	arg_parser = argparse.ArgumentParser(description="Load analytics log events from a file.")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							 dest='verbose')
	arg_parser.add_argument('-s', '--site', dest='site', help="Request site")
	arg_parser.add_argument('-f', '--file',
							dest='filename',
							help="The file containing the events.")

	args = arg_parser.parse_args()
	site = args.site
	file_name = args.filename
	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")

	context = create_context(env_dir, with_library=True)
	conf_packages = ('nti.analytics', 'nti.appserver',)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						verbose=args.verbose,
						context=context,
						minimal_ds=True,
						function=lambda: _process_args(site=site,
													   file_name=file_name))

if __name__ == '__main__':
	main()
