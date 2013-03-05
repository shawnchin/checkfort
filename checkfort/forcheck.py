import os
import re
import sys
import pexpect
import subprocess
from tempfile import mkstemp
from glob import glob1 as sieve

from checkfort.exceptions import *
from checkfort.parser import ForcheckParser
from checkfort.logging import p_info, p_verbose, p_warn, p_error
from checkfort.logging import verbose_enabled

# we support only version 14.2 and above
#  - versions before 14.1 has a slightly different output format
#  - Dependency calculation in 14.1 seems slightly off so files are not
#    arranged in the right order and we end up with "module not found" errors
MIN_VESION = "14.2"

DEFAULT_ARGS = ["-nshinc",    # Don't list statements of include files
                "-plen 999",  # Reduce the number of page breaks
                "-pwid 255",  # Place maximum possible characters (255)
                              #  on a line
                "-batch"]     # Batch mode

SUPPORTED_STANDARDS = {"77": "-f77",
                       "90": "-f90",
                       "95": "-f95",
                       "2003": "-f03",
                       "2008": "-f08"}

EXIT_CODES = {
    0: "no informative, warning, overflow or error messages presented",
    2: "informative, but no warning, overflow or error messages presented",
    4: "warning, but no overflow or error messages presented",
    6: "table overflow, but no error messages presented",
    8: "error messages presented"}


class Forcheck(object):
    def __init__(self, input_files,
                 fortran_standard="95",
                 emulate_compiler="gfortran",
                 free_format=False, extra_opts=None):
        self.rc = None
        self.input_files = input_files
        self.extra_opts = extra_opts

        # create tempfile file for use as staging area for forcheck .lst file
        tmp_fd, self.tmpfile = mkstemp(suffix=".lst")
        os.close(tmp_fd)

        # The following are set by call to self._locate_forcheck()
        self.supported_emulators = []
        self.cnfdir = None
        self.forcheck_exe = None
        self.forcheck_version = None
        self._locate_forcheck()

        # we support only version 14.2 and above
        ver = self.get_version()

        # store layout format and language standard
        self.free_format = free_format
        if fortran_standard not in SUPPORTED_STANDARDS:
            raise CheckfortException("Unsupported Fortran standard. "
                                     "Possible options: "
                                     + ", ".join(SUPPORTED_STANDARDS.keys()))
        self.fortran_standard = fortran_standard

        # select compiler emulation
        if emulate_compiler not in self.supported_emulators:
            raise CheckfortException("Unsuppoted compiler emulation. "
                                     "Possible options: "
                                     + ", ".join(self.supported_emulators))
        self.emulate_compiler = emulate_compiler
        os.environ["FCKCNF"] = os.path.join(self.cnfdir,
                                            "%s.cnf" % emulate_compiler)
        p_info(" - compiler emilation: %s" % emulate_compiler)

    def __del__(self):
        if self.tmpfile and os.path.isfile(self.tmpfile):
            os.unlink(self.tmpfile)

    def get_tmp_filename(self):
        return self.tmpfile

    def _locate_forcheck(self):
        """
        Detect required environment variables (FCKDIR, FCKCNF).

        From those values, locate forchk binary and detects list of supported
        compiler emulators.

        sets self.cnfdir, self.forcheck_exe and self.supported_emulators
        """
        p_info("\nLocating forcheck")

        if "FCKPWD" not in os.environ:
            raise CheckfortException("FCKPWD environment var not set")

        try:
            fdir = os.environ["FCKDIR"]
        except KeyError:
            raise CheckfortException("FCKDIR environment var not set")

        # locate exe
        candidates = map(lambda x: os.path.join(fdir, x, "forchk"),
                            ("bin", "."))
        try:
            found = (x for x in candidates if os.path.isfile(x)).next()
        except StopIteration:
            raise CheckfortException("Could not find 'forchk' binary")
        self.forcheck_exe = os.path.realpath(os.path.join(fdir, found))

        # locate g95.cnf and assume all cnf files are in the same dir
        candidates = map(lambda x: os.path.join(fdir, x, "g95.cnf"),
                            ("share/forcheck", "."))
        try:
            found = (x for x in candidates if os.path.isfile(x)).next()
        except StopIteration:
            raise CheckfortException("Could not find '*.cnf' files")
        self.cnfdir = os.path.dirname(os.path.join(fdir, found))

        # detect list of supported emulators
        self.supported_emulators = [x[:-4] for x in sieve(self.cnfdir,
                                                          "*.cnf")]

        # guess version number by doing a trial run of forchk
        try:
            child = subprocess.Popen([self.forcheck_exe, "-batch"],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        except:
            raise CheckfortException("Could not run " + self.forcheck_exe)

        # extract version string from output header
        first_line = child.communicate()[0].split("\n", 1)[0]
        last_col = first_line.rsplit(None, 1)[1]
        try:
            ver = re.match(r"V(\d+)\.(\d+)\.(\d+)", last_col).groups()
            self.forcheck_version = map(int, ver)
        except AttributeError:
            raise CheckfortException(
                self.forcheck_exe + " not producing expected output")

        p_info(" - install dir: %s" % fdir)
        p_info(" - executable: %s" % self.forcheck_exe)
        p_info(" - version: %s" % ".".join(str(v)
                                                 for v in self.get_version()))

        # compare min version
        min_ver = tuple(int(x) for x in MIN_VESION.split("."))
        if tuple(self.forcheck_version[:2]) < min_ver[:2]:
            p_error("Unsupported Forcheck version "
                    "(version >=%s expected)." % MIN_VESION)

    def get_arguments(self):
        args = DEFAULT_ARGS[:]
        args.append(SUPPORTED_STANDARDS[self.fortran_standard])
        if self.free_format:
            args.append("-ff")
        if self.extra_opts:
            args.extend(self.extra_opts)
        return args

    def get_version(self):
        return self.forcheck_version

    def get_command(self):
        return ([self.forcheck_exe, "-l", self.tmpfile]
                    + self.get_arguments() + self.input_files)

    def _report_runtime_message(self, line):
        """Selectively print content from forcheck runtime output"""
        line = line.strip()

        if line.startswith("-- "):
            if line.startswith("-- file: "):
                p_verbose("    - %s" % line.split(None, 2)[2])
            elif not line.startswith("-- commandline") and \
                    not line.startswith("-- messages presented"):
                p_verbose(line)
            if not verbose_enabled():
                p_info(".", "")

        elif line.startswith("FCK-- "):
            err = line.split(None, 1)[1]
            culprit, filename = self._store_prev
            if not filename.startswith("("):
                filename = ""  # not specified
            p_warn("%s - %s %s\n" % (err, culprit, filename))

        elif not verbose_enabled() and line.startswith("- file"):
            p_info(".", "")

        self._store_prev = (line, self._store_prev[0])

    def get_run_data(self):
        return {
            "rc": self.rc,
            "rc_message": EXIT_CODES[self.rc],
            "command": " ".join(self.get_command()),
            "version_string": "Forcheck version %s" % \
                              ".".join(str(x) for x in self.get_version()),
        }

    def run(self):
        out = "forcheck.log"
        p_info("\nRunning forcheck (stdout written to %s)" % out)
        with open(out, "w") as fout:
            # use pexpect.spawn instead of subprocess.Popen so we can get
            # real-time output from forcheck (Popen is subject to stdout being
            # buffered when redirected to PIPE).
            cmd = self.get_command()
            child = pexpect.spawn(cmd[0], args=cmd[1:], logfile=fout)
            self._store_prev = ("", "")
            while True:
                try:
                    child.expect('\n')
                    self._report_runtime_message(child.before)
                except pexpect.EOF:
                    break
            child.close()
            self.rc = child.exitstatus
        try:
            p_info("\nDONE. (rc=%d, %s)" % (self.rc, EXIT_CODES[self.rc]))
        except KeyError:
            p_error("FAILED (rc=%d). See %s for details" % (self.rc, out))
