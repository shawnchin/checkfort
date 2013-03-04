import sys

_debug = False
_verbose = False
_info = True


def set_silent_mode(silent=True):
    global _verbose, _info
    _verbose = not silent
    _info = not silent


def set_verbose_mode(verbose=True):
    global _verbose
    _verbose = verbose


def set_debug_mode(debug=True):
    global _debug
    _debug = debug


def debug_enabled():
    return _debug


def verbose_enabled():
    return _verbose


def p_debug(msg, endl="\n"):
    if _debug:
        sys.stderr.write("(DEBUG) %s%s" % (msg, endl))
        sys.stderr.flush()


def p_verbose(msg, endl="\n"):
    if _verbose:
        sys.stdout.write("%s%s" % (msg, endl))
        sys.stdout.flush()


def p_info(msg, endl="\n"):
    if _info:
        sys.stdout.write("%s%s" % (msg, endl))
        sys.stdout.flush()


def p_warn(msg, endl="\n"):
    sys.stderr.write("(Warning) %s%s" % (msg, endl))
    sys.stderr.flush()


def p_error(msg, rc=100, endl="\n"):
    sys.stderr.write("(Error) %s%s" % (msg, endl))
    sys.exit(rc)
