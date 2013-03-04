import os
import sys
from setuptools import setup

from checkfort import __version__ as version
from checkfort import project_url


if sys.hexversion < 0x02060000:
    raise RuntimeError('This package requires Python 2.6 or later')


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="checkfort",
    version=version,
    author="Shawn Chin",
    author_email="shawn.chin@stfc.ac.uk",
    description=("A wrapper tool for FORCHECK."),
    license="BSD",
    keywords="fortran forcheck static_analysis software_tools",
    url=project_url,
    packages=['checkfort'],
    include_package_data=True,
    long_description=read('README'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Utilities",
        ],
    install_requires=["pygments >= 1.4", "jinja2", "chardet", "pexpect"],
    entry_points={"console_scripts": ["cfort", "checkfort.launcher:main"]}
)
