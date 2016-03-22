=====================
Analytics Tables
=====================

This document provides a summary of the database tables storing analytics data.

.. note:: Updated March 21, 2016

Concepts
========

These are some basic concepts common on many tables below.

context_path
	A list of dataserver NTIIDs, describing how the user accessed the
	particular resource (e.g. video, reading, etc), perhaps from an
	activiy stream or via lessons in a course outline.

user_id
	Linked to a user in the `Users` table.

course_id
	Linked to a course in the `Courses` table. Many tables are
	rooted in a course entry.

session_id
	Linked to a session in the `Sessions` table. The logical
	session associated with a given event.

timestamp
	The UTC timestamp associated with a particular event.

time_length
	The time length, in seconds, in which the event lasted.

Tables
========

AssignmentDetailGrades
	A table that breaks down grades per question in an assignment taken.
	Allows multiple graders to grade a particular assignment.

AssignmentDetails
	Describes the assignment submission at a question level, storing the
	submission for a particular question in an assignment.

AssignmentFeedback
	Captures feedback left on assignments between students and instructors,
	including the textual length.

AssignmentGrades
	Stores the grader and grade (alpha-numeric and numeric) given to a student
	in a particular assignment.

AssignmentViews
	Stores assignment views for a particular user.

AssignmentsTaken
	Describes an assignment taken by a user, including whether the assignment was
	submitted after its due date. These entries will typically map to
	`AssignmentDetails` and `AssignmentGrades`. Information is also stored on
	how long the user took to take the assignment.

BlogCommentFavorites
	Stores which users 'favorited' blog comments, as well as information on the
	creator of the original blog comment.

BlogCommentLikes
	Captures information on which users 'liked' blog comments, as well as
	information on the creator of the original blog comment.

BlogCommentsCreated
	Describes a blog comment created, including like/favorite counts, flagged
	for reporting, as well as the parent_id and parent_user_id of a possible
	parent blog comment.

BlogCommentsUserFileUploadMimeTypes
	Stores mime_type information (e.g. 'image/jpeg') and counts for that mime_type
	on file uploads for a particular blog comment.

BlogFavorites
	Stores events when users favorite blogs.

BlogLikes
	Captures data on users liking blogs.

BlogsCreated
	Describes a blog entry creation event, including like/favorite count, reported,
	and the length of the blog post.

BlogsViewed
	Captures information when a user views a blog.

BookmarksCreated
	Stores information when a user creates a bookmark, typically on a piece of
	content.

Books
	Describes top-level books, existing in the library view. These are
	created lazily on demand.

ChatsInitiated
	Captures information when a user initiates a chat with another user.

ChatsJoined
	Captures information when a user joins a chat.

ContactsAdded
	Stores data when a user adds another user as a contact (e.g. friends).

ContactsRemoved
	Stores data when a user removes another user as a contact.

ContextId
	An ID generated table for Books/Courses. Contains no data.

CourseCatalogViews
	Captures information when a user views a course catalog entry (before
	possibly enrolling).

CourseDrops
	Stores information when a user drops a course.

CourseEnrollments
	Stores information about a user enrolling in a course.

CourseResourceViews
	Captures data when a user views a particular course resource (linked to
	the `Resources` table), including how long the resource was viewed
	(in seconds).

Courses
	Describes courses. These are created lazily on demand.

DynamicFriendsListsCreated
	Stores information when a DynamicFriendsList (DFL) is created.

DynamicFriendsListsMemberAdded
	Stores information when a DynamicfriendsList (DFL) adds a member.

DynamicFriendsListsMemberRemoved
	Stores information when a DynamicfriendsList (DFL) removes a member.

EnrollmentTypes
	Stores information on different enrollment types (e.g. Public, ForCredit, etc).
	Linked to via the CourseEnrollments table.

EntityProfileActivityViews
	Contains information when an entity's (e.g. user, community, etc)
	activity profile is viewed by another user.

EntityProfileMembershipViews
	Contains information when an entity's (e.g. user, community, etc)
	membership profile information is viewed by another user.

EntityProfileViews
	Contains information when an entity's (e.g. user, community, etc) profile
	is viewed by another user.

FeedbackUserFileUploadMimeTypes
	Stores mime_type information (e.g. 'image/jpeg') and counts for that mime_type
	on file uploads for a particular assignment feedback.

FileMimeTypes
	Contains all file mime_types for file uploads (in the ...FileUploadMimeTypes
	tables).

ForumCommentFavorites
	Describes forum comments 'favorited' by a user.

ForumCommentLikes
	Describes forum comments 'liked' by a user.

ForumCommentsCreated
	Captures information on forum comments created by a user, including like/favorite
	count, reporting flag, textual length, as well as links to the containing topic
	and forum. Parent comment information is also contained here, if available.

ForumCommentsUserFileUploadMimeTypes
	Stores mime_type information (e.g. 'image/jpeg') and counts for that mime_type
	on file uploads for a particular forum comment.

ForumsCreated
	Contains information when a forum is created.

FriendsListsCreated
	Contains data on FriendsLists created by a user.

FriendsListsMemberAdded
	Contains information when users are added to a FriendsList.

FriendsListsMemberRemoved
	Contains information when users are removed from a FriendsList.

HighlightsCreated
	Captures information when a user creates a highlight on content.

IpGeoLocation
	Stores a users IP address when not used before. Along with this, a
	geographical location is referenced in the `Location` table.

Location
	Holds geographical location for a particular latitude and longitude
	coordinates, including city, state, and country.

NoteFavorites
	Describes notes 'favorited' by a user.

NoteLikes
	Describes notes 'liked' by a user.

NotesCreated
	Holds data on notes created by users on the content (via the `Resources`
	table). Information is also stored on like/favorite counts, textual
	length, as well as parent note information (if available). Sharing
	data is also included, describing how a user shares a note with others.

NotesUserFileUploadMimeTypes
	Stores mime_type information (e.g. 'image/jpeg') and counts for that mime_type
	on file uploads for a particular note.

NotesViewed
	Describes when a user views a note in content.

PollsTaken
	Captures information when a user takes a poll question.

Resources
	Describes resources (e.g. content) as dataserver NTIIDs. Other tables link
	to this table when resources are viewed. Video resources will also have a
	max_time_length value containing the duration of the video.

SearchQueries
	Captures information on user searches, including the terms searched for.
	Data is also captured on query time, number of hits returned, and whether
	the user filters by search type (content, video, reading, etc). The user
	may also root the search on a particular course.

SelfAssessmentDetails
	Contains per-question information on SelfAssessment submissions, including
	grade and if the submission is correct.

SelfAssessmentViews
	Stores information on users viewing SelfAssessments.

SelfAssessmentsTaken
	Captures information when a user submits a SelfAssessment.

Sessions
	Contains information on a user's logical session, including start and end
	time, user agent (via the UserAgents table), and the IP address associated
	with the session.

SurveysTaken
	Describes data when a user takes a survey of poll questions.

TopicFavorites
	Describes topics 'favorited' by a user.

TopicLikes
	Describes topics 'liked' by a user.

TopicsCreated
	Holds information when a user creates a topic in a forum, including
	like/favorite count, reporting flag, and the containing forum identifier.

TopicsViewed
	Store information when a user views a particular topic, including how
	long they viewed it.

UserAgents
	Holds the user agent string associated with requests. This information
	allows extrapolation of user device/browser usage.

UserFileUploadViewEvents
	Holds information when a user views a file uploaded by another user (in a
	note/feedback/forum comment, etc). We also store which user uploaded the
	file and what particular mime_type the file is.

Users
	Captures information on users. A `username2` column is used if some clients
	may have alternate usernames. The `allow_research` column is available if
	clients want to allow users to opt-in/out of research. Users are lazily
	created when analytics events are created referencing them.

VideoEvents
	Stores information on videos viewed by users, including at what time in the
	video the user started/stopped (in seconds, time 0 is the beginning of the
	video), if the user used the transcript or not, 'video_event_type' is an
	enum of `WATCH` or `SKIP`, how long the user watched the video, and the play
	speed captured at the end of the video view event. If the event is `SKIP`,
	the start time is the time (in video seconds) which the user moved the cursor
	from to the end time, the time (in video seconds) the user moved the cursor to.

VideoPlaySpeedEvents
	Stores information when a user changes the play speed during a video,
	including the old play speed, the new play speed, and the time in the
	video (in video seconds) when the play speed changed.
