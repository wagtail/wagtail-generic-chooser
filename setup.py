#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='wagtail-generic-chooser',
    version='0.4.1',
    description="A toolkit for custom chooser popups in Wagtail",
    author='Matthew Westcott',
    author_email='matthew.westcott@torchbox.com',
    url='https://github.com/wagtail/wagtail-generic-chooser',
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    install_requires=[
        'requests>=2.11.1,<3.0',
    ],
    license='BSD',
    long_description="""
        Base classes for building chooser popups and form widgets for the Wagtail admin,
        matching Wagtail's built-in choosers and backed by either models or a REST API
    """,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Django',
        'Framework :: Wagtail',
        'Framework :: Wagtail :: 2',
        'Framework :: Wagtail :: 3',
    ],
)
