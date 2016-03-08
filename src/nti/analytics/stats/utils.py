#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from math import sqrt

from nti.analytics.stats.model import TimeStats
from nti.analytics.stats.model import CountStats

from nti.dataserver_core.interfaces import ICanvas

def get_std_dev(values, summation=None):
	result = None
	if values:
		count = len(values)
		summation = summation if summation else sum(values)
		sum_of_squares = sum([x ** 2 for x in values if x is not None])
		variance = sum_of_squares / count - (summation / count) ** 2
		result = sqrt(variance)
	return result

def get_count_stats(records):
	"""
	For a sequence of records, return Stats.
	"""
	count = 0
	if records is not None:
		count = len(records)
	stats = CountStats(Count=count)
	return stats

def get_time_stats(time_lengths):
	"""
	For a sequence of time lengths, return the TimeStats.
	"""
	total_time = std_dev = average = count = 0
	if time_lengths:
		total_time = sum(time_lengths)
		count = len(time_lengths)
		average = total_time / count
		std_dev = get_std_dev(time_lengths, total_time)

	stats = TimeStats(AggregateTime=total_time,
					  StandardDeviationDuration=std_dev,
					  AverageDuration=average,
					  Count=count)
	return stats

def _has_whiteboard(obj):
	body = obj.body
	if body:
		for body_part in body:
			if ICanvas.providedBy(body_part):
				return True
	return False

def build_post_stats(records, clazz, obj_field, length_field):
	"""
	Given post (comment/blog/note/etc) records, build a post stats object
	using the given factory.
	"""
	count = reply_count = top_level_count = 0
	distinct_like_count = distinct_fave_count = 0
	total_likes = total_faves = total_length = 0
	recursive_child_count = contains_board_count = 0
	average_length = std_dev_length = 0

	if records:
		lengths = []

		for post in records:
			count += 1
			if post.IsReply:
				reply_count += 1
			else:
				top_level_count += 1

			if post.LikeCount:
				distinct_like_count += 1
				total_likes += post.LikeCount

			if post.FavoriteCount:
				distinct_fave_count += 1
				total_faves += post.FavoriteCount

			post_length = getattr(post, length_field, None)

			if post_length is not None:
				lengths.append(post_length)
				total_length += post_length

			obj = getattr(post, obj_field, None)

			if obj is not None:
				# Waking up object, expensive if we're
				# waking up every child?
				recursive_child_count += len(obj.referents)

				if _has_whiteboard(obj):
					contains_board_count += 1

		average_length = total_length / count
		std_dev_length = get_std_dev(lengths, total_length)

	post_stats = clazz(Count=count,
					   ReplyCount=reply_count,
					   TopLevelCount=top_level_count,
					   DistinctPostsLiked=distinct_like_count,
					   DistinctPostsFavorited=distinct_fave_count,
					   TotalLikes=total_likes,
					   TotalFavorites=total_faves,
					   RecursiveChildrenCount=recursive_child_count,
					   StandardDeviationLength=std_dev_length,
					   AverageLength=average_length,
					   ContainsWhiteboardCount=contains_board_count)

	return post_stats
