#!/usr/bin/env python
"""
%prog [OPTIONS] files...        # Run forcheck on given files
%prog [OPTIONS] dirs...         # Run forcheck on source files in dirs
%prog [OPTIONS] -I SOURCE_FILE  # Load files/dirs from SOURCE_FILES as input
%prog [OPTIONS] (any combination of the above three)

%prog [-h|--help]               # Display program options
%prog [--version]               # Display version information
"""
import os
import sys
import shlex
from optparse import OptionParser
from checkfort.exceptions import *
from checkfort.forcheck import SUPPORTED_STANDARDS, Forcheck
from checkfort import __version__ as version
from checkfort.logging import set_silent_mode, set_verbose_mode, set_debug_mode
from checkfort.logging import p_info, p_debug, p_verbose, p_warn, p_error
from checkfort.files import InputFileReader, FileList, default_extensions
from checkfort.parser import ForcheckParser
from checkfort.filegen import ResultWriter

outdir = "cfort_html"
supported_standards = SUPPORTED_STANDARDS.keys()
default_standard = "95"
default_emulation = "gfortran"
header = "CheckFort (Version %s)" % version


def main():
    o, a = parse_options()

    cleaned = {}  # store validated input options
    cleaned["outdir"] = o.outdir
    cleaned["pretend"] = bool(o.pretend)
    cleaned["extra_opts"] = shlex.split(o.extra_opts or "")

    # --compiler-emulation can only be checked once Forcheck is found.
    # Accept anything for now
    cleaned["emulation"] = o.emulation

    # Set log level
    if o.quiet or cleaned["pretend"]:
        set_silent_mode()
    elif o.verbose:
        set_verbose_mode()
    if o.debug:
        set_debug_mode()

    # Once output verbosity set, we can print the output header
    p_info("%s" % header)

    # check allowed standards
    if o.standard not in supported_standards:
        p_error("Unsupported fortran standard (%s). Options: %s"
                % (o.standard, ", ".join(supported_standards)))
    else:
        cleaned["standard"] = o.standard

    # deal with optional --free-form
    if o.free_form:
        if cleaned["standard"] == '77':
            p_warn("Fortran 77 does not support free format. Ignoring "
                   "--free-form (-f) option.")
            o.free_form = False
    cleaned["free_format"] = bool(o.free_form)

    # check --ignore-err-codes (must be comma separated numeric codes)
    try:
        cleaned["ignore_list"] = list(set(int(x) for x in o.ignore.split(",")
                                                     if x.strip()))
    except ValueError:
        p_error("Invalid value for --ignore-err-codes (-i). "
                "Expecting comma-separated list of numeric values")

    # read target files form positional args and --input-file option
    targets = a[:]  # get targets from arguments
    if o.input_file:  # get targets from file specified with --input-file
        try:
            targets.extend(InputFileReader(o.input_file).get_entries())
        except IOError:
            p_error("Input file not readable: %s" % o.input_file)
    if not targets:
        p_error("No inputs provided.")

    # file extensions to search for
    if o.extensions:
        ext_list = [x.strip() for x in o.extensions.split(",")]
    else:
        ext_list = default_extensions

    # search and validate target files
    if any(os.path.isdir(x) for x in targets):
        p_info("Searching directories for files with the following "
                  "extensions : %s" % " ".join("*.%s" % x for x in ext_list))
    try:
        filelist = FileList(targets,  ext_list)
    except CheckfortException, e:
        p_error(e)

    if not filelist.files:
        p_error("No relevant input files found.")
    cleaned["files"] = filelist.files

    # do actual work
    try:
        do_action(cleaned)
    except CheckfortException, e:
        p_error(e)


def do_action(params):
    f = Forcheck(params["files"],
                 fortran_standard=params["standard"],
                 emulate_compiler=params["emulation"],
                 free_format=params["free_format"],
                 extra_opts=params["extra_opts"])

    if params["pretend"]:
        print " ".join(f.get_command())
        sys.exit(0)

    # run forcheck
    f.run()
    forcheck_output = f.get_tmp_filename()  # file deleted by f.__del__()

    # parse
    parser = ForcheckParser(forcheck_output, ignore_list=params["ignore_list"])

    # result state
    state = parser.state
    state.run_data = f.get_run_data()

    # generate output
    writer = ResultWriter(parser.state, params["outdir"])
    writer.run()

    p_info("\nAll done. View '%s/index.html' for results." % params["outdir"])


def parse_options():
    op = OptionParser(usage=__doc__, version=header)
    op.set_defaults(quiet=False, verbose=False, debug=False, free_form=False,
                    standard=default_standard, outdir=outdir, ignore="",
                    emulation=default_emulation)
    op.add_option("-q", "--quiet", action="store_true", dest="quiet",
                  help="Suppress program output")
    op.add_option("-v", "--verbose", action="store_true", dest="verbose",
                  help="Print progress information")
    op.add_option("-d", "--debug", action="store_true", dest="debug",
                  help="Print debug information")
    op.add_option("-p", "--pretend", action="store_true", dest="pretend",
                  help="Don't run forcheck. Instead, display command that "
                       "would have been used. Also implies --quiet.")
    op.add_option("-f", "--free-form", action="store_true", dest="free_form",
                  help="Specify free form source layout for all files. "
                       "(default: let forcheck decide based on file "
                       "extensions)")
    op.add_option("-e", "--file-extensions", type="string", dest="extensions",
                   help="Extensions to search for when traversing directories "
                        "(default: '%s')" % ",".join(default_extensions))
    op.add_option("-s", "--fortran-standard", type="string", dest="standard",
                   help="Fortran standard to validate against. "
                        "(default: '%s', options: '%s')"
                        % (default_standard, "', '".join(supported_standards)))
    op.add_option("-c", "--compiler-emulation", type="string",
                  dest="emulation",
                  help="Compiler to emulate (default: %s)" % default_emulation)
    op.add_option("-i", "--ignore-err-codes", type="string", dest="ignore",
                  help="Comma-separated ist of error codes to ignore. "
                       "For example: --ignore-err-codes='234,153,9'")
    op.add_option("-o", "--extra-options", type="string", dest="extra_opts",
                   help="Pass extra options to forcheck. (Note that some "
                        "options changes forcheck's output which may affect "
                        "checkfort's ability to parse the results.)")
    op.add_option("-O", "--output-dir", type="string", dest="outdir",
                  help="Change output directory (default: %s)" % outdir)
    op.add_option("-I", "--input-file", type="string", dest="input_file",
                  help="Provide a file which contains a list of files/dirs "
                       "to use as input.")

    return op.parse_args()


if __name__ == "__main__":
    main()
