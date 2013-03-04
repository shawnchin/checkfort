import os
import re
import sys
from checkfort.exceptions import *
from checkfort.logging import p_warn, p_verbose

default_extensions = ("h", "f", "F",
                      "f90", "F90", "f95", "F95",
                      "f03", "F03", "f08", "F08", "h",)


class InputFileReader(object):
    def __init__(self, input_file):
        with open(input_file) as f:
            lines = (re.split(r'[#!]', x, 1)[0].strip() for x in f)
            self.entries = list(x for x in lines if x)

    def get_entries(self):
        return self.entries


class FileList(object):
    def __init__(self, entries=None, extensions=default_extensions):
        self.files = []
        # build regex from extension list
        if not extensions:
            raise CheckfortException("Invalid extensions list - " + extensions)
        self.extensions = extensions
        self.re_extensions = re.compile(".*\.(%s)$" % "|".join(extensions))

        if entries:
            self.add_files(entries)

    def add_files(self, entries):
        if isinstance(entries, basestring):
            self._add(entries)
        else:
            for entry in entries:
                self._add(entry)

    def _check_and_add(self, filename):
        if not os.path.exists(filename):
            if os.path.islink(filename):
                p_warn("Warning: ignoring broken sym link - (%s)" % filename)
                return
            else:
                raise CheckfortException("Invalid path - " + filename)
        assert(not os.path.isdir(filename))
        self.files.append(os.path.relpath(filename))

    def _add(self, entry):
        if os.path.isdir(entry):
            self._search_dir(entry)
        else:
            self._check_and_add(entry)

    def _search_dir(self, directory):
        p_verbose(" - Searching for files in %s" % directory)
        for root, dirs, files in os.walk(os.path.relpath(directory)):
            for f in files:
                if self.re_extensions.match(f):
                    self._check_and_add(os.path.join(root, f))
