import codecs
from setuptools import setup, find_packages

VERSION = '0.0.0'

entry_points = {
    'console_scripts': [
        "nti_analytics_migrator = nti.analytics.utils.ds_migrator:main",
        "nti_analytics_database_migrator = nti.analytics.utils.database_migrator:main",
        "nti_analytics_event_uploader = nti.analytics.utils.event_uploader:main",
        "nti_analytics_video_duration = nti.analytics.utils.upload_video_durations:main",
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
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['nti'],
    install_requires=[
        'setuptools',
        'alembic',
        'geopy',
        'nti.analytics_database',
        'nti.app.assessment',
        'nti.app.products.courseware',
        'nti.app.products.courseware_scorm',
        'nti.app.products.courseware_ims',
        'nti.app.products.gradebook',
        'nti.asynchronous',
        'nti.contenttypes.completion',
        'nti.namedfile',
        'python-geoip',
        'python-geoip-geolite2',
        'sqlalchemy',
        'user-agents',
        'zope.deferredimport',
        'zope.deprecation',
    ],
    extras_require={
        'test': [
            'fudge',
            'nti.app.testing'
        ]
    },
    entry_points=entry_points
)
