import codecs
from setuptools import setup, find_packages

VERSION = '0.0.0'

entry_points = {
	'console_scripts': [
		"nti_analytics_processor = nti.analytics.utils.constructor:main",
		"nti_analytics_migrator = nti.analytics.utils.ds_migrator:main",
		"nti_analytics_fail_processor = nti.analytics.utils.failure_processor:main",
		"nti_analytics_video_duration = nti.analytics.utils.upload_video_durations:main",
		"nti_analytics_event_uploader = nti.analytics.utils.event_uploader:main"
	],
}

setup(
	name='nti.analytics',
	version=VERSION,
	author='Josh Zuech',
	author_email='josh.zuech@nextthought.com',
	description="NTI Analytics",
	long_description=codecs.open('README.rst', encoding='utf-8').read(),
	license='Proprietary',
	keywords='pyramid preference',
	classifiers=[
		'Intended Audience :: Developers',
		'Natural Language :: English',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.3',
	],
	packages=find_packages('src'),
	package_dir={'': 'src'},
	namespace_packages=['nti'],
	install_requires=[
		'setuptools',
		'alembic',
		'geopy',
		'python-geoip',
		'python-geoip-geolite2',
		'sqlalchemy',
		'user-agents',
		'nti.analytics_database',
		'nti.app.assessment',
		'nti.app.products.courseware',
		'nti.app.products.courseware_ims',
		'nti.app.products.gradebook',
		'nti.async'
	],
	entry_points=entry_points
)
