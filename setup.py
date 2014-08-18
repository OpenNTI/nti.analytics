import codecs
from setuptools import setup, find_packages

VERSION = '0.0.0'

entry_points = {
    'console_scripts': [
        "nti_analytics_processor = nti.analytics.utils.constructor:main",
        "nti_analytics_migrator = nti.analytics.utils.ds_migrator:main",
    ],
}

setup(
    name='nti.analytics',
    version=VERSION,
    author='Josh Zuech',
    author_email='josh.zuech@nextthought.com',
    description="NTI analytics",
    long_description=codecs.open('README.rst', encoding='utf-8').read(),
    license='Proprietary',
    keywords='pyramid preference',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
		'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        ],
	packages=find_packages('src'),
	package_dir={'': 'src'},
	namespace_packages=['nti'],
	install_requires=[
		'setuptools',
		'nti.async'
	],
	entry_points=entry_points
)
