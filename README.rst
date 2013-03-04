==================================
CheckFort : A wrapper for Forcheck
==================================

CheckFort is a wrapper for Forcheck_, a static analyser for Fortran.
CheckFort aims to simplify the launching of the forcheck and reformats its
output into a format which we believe to be easier to navigate.


Dependencies:
=============

* A valid installation of FORCHECK (version >=14.2)
* Python >=2.6
* pygments >=1.4
* chardet
* jinja2
* pexpect


Usage:
======

To use CheckFort, you need a valid Forcheck_ installation. The following
environment variables must be set:

* FCKDIR : Forcheck installation directory
* FCKPWD : Path to Forcheck license file

You can then run:

    cfort [options] files/dirs...

Run `cfort --help` for more options.


Disclaimer:
===========

CheckFort is developed independently from Forcheck


License:
========

This software is licensed under the OSI-approved "3-clause BSD License". 
See the included LICENSE.txt file.


.. Forcheck_: http://www.forcheck.nl/
 
 
