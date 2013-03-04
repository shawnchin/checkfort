import re
import sys
from collections import defaultdict, namedtuple

from checkfort.exceptions import *
from checkfort.logging import p_debug, p_verbose, p_info


class EventInstance(object):
    def __init__(self, code, culprit, linenum=None, filename=None):
        assert not filename or "../" not in filename
        self.code = code
        self.culprit = culprit
        self.filename = filename
        if not linenum is None:
            self.linenum = int(linenum)
        else:
            self.linenum = None

    @property
    def link(self):
        if not self.filename:
            return None
        return "src/%s.html#line-%d" % (self.filename.replace(' ', '_'),
                                        self.linenum)


class ParserState(object):
    def __init__(self, legacy_mode=False, ignore_list=None):
        self.legacy_mode = legacy_mode
        self.sums = {}
        self.event_message = defaultdict(str)
        self.event_counter = defaultdict(int)
        self.event_instances = defaultdict(list)
        self.file_events = defaultdict(list)
        #self.global_events = defaultdict(list)
        self.ignore_list = set(int(x) for x in ignore_list)
        self.debug_required = False

    def _should_ignore(self, code):
        if not self.ignore_list:
            return False
        numeric, syntax = code.split(None, 1)
        return (int(numeric) in self.ignore_list)

    def _store_event(self, code, message, instance):
        if self._should_ignore(code):
            return
        self.event_instances[code].append(instance)
        self.event_counter[code] += 1

        if not code in self.event_message:
            self.event_message[code] = message
        else:
            if message != self.event_message[code]:
                self.debug_required = True
                p_debug("Seeing different messages for "
                                 "event code (%s).\n" % code)

    def store_sums(self, name, total):
        self.sums[name] = total

    def store_file_event(self, filename, linenum, code, message, culprit):
        if self._should_ignore(code):
            return
        instance = EventInstance(code, culprit, linenum, filename)
        self._store_event(code, message, instance)
        if filename is not None:
            self.file_events[filename].append(instance)

    def store_global_event(self, code, message, details):
        if self._should_ignore(code):
            return
        instance = EventInstance(code, details)
        self._store_event(code, message, instance)
        #self.global_events[code].append(instance)


class ForcheckParser(object):
    # set legacy mode for forcheck version <14.1
    def __init__(self, forcheck_listfile,
                 legacy_mode=False, ignore_list=None):
        self.listfile = forcheck_listfile
        self.state = ParserState(legacy_mode, ignore_list=ignore_list)
        self._parse()

    def _parse(self):
        p_info("\nParsing forcheck listfile")
        if self.state.ignore_list:
            p_info("(ignoring the following forcheck events: "
                   "%s)" % ", ".join(str(x) for x in self.state.ignore_list))

        stages = iter((
            {"name": "file events",
             "end_marker": "global program analysis:",
             "parser": FileEvent(self.state)},
            {"name": "global events",
             "end_marker": "program_units and procedures analysed:",
             "parser": GlobalEvent(self.state)},
            {"name": "program units",
             # "end_marker": "*END OF ANALYSIS*"  # no longer appear in >14.3
             "end_marker": "messages presented:",
             "parser": None},
            {"name": "forcheck summary",
             "end_marker": None,
             "parser": SummaryEvent(self.state)},
        ))

        lines = ("", "", "")  # (current, previous, previous-1)
        stage = stages.next()
        p_info(" - Parsing %s" % stage["name"])

        def forward_to_content(file_iterator):
            """
            Forwards file iterator the the actual content, then returns
            the source file addressed by forcheck output page
            """
            # each new page starts with a header
            line = next(file_iterator)
            assert line.startswith("FORCHECK"), "Unexpected listfile format"

            # this is followed by "(options...) target_file" if the output is
            # file specific
            line = next(file_iterator)
            if line.strip():
                target_file = line.rsplit(None, 1)[-1]
                line = next(file_iterator)  # following line should be blank
                assert not line.strip(), "Unexpected listfile format"
            else:
                target_file = None
            return target_file

        with open(self.listfile) as f:
            target_file = forward_to_content(f)
            for L in f:
                if L.startswith("\f"):  # new page. forward to content
                    target_file = forward_to_content(f)
                    continue
                lines = (L.strip(), lines[0], lines[1])  # shift
                if lines[0] == stage["end_marker"]:
                    stage = stages.next()
                    p_info(" - Parsing %s" % stage["name"])
                elif stage["parser"]:  # if event has a parser
                    stage["parser"].slurp(target_file, *lines)

        if self.state.debug_required:
            import shutil
            listfile_out = "forcheck_listfile.debug"
            shutil.copy(self.listfile, listfile_out)
            p_debug(
                "There appears to be a problem in the parsing. \n"
                " Forcheck results written to %s. \n"
                " Please send the file and the checkfort version info\n"
                "    to the checkfort devs for further investigation"
                % (listfile_out, ))
        else:
            p_verbose("Parse successful")


class Event(object):
    """Base class for Event parsers"""

    # precompile frequently used regex patterns
    re_err = re.compile(r"^\*\*\[\s*(\d+ [IEWO])\] (.*)")
    re_file = re.compile(r"^\(file: ([^,]+), line:\s+(\d+)\)")
    re_summary = re.compile(r"^(\d+)x\[\s*(\d+ [IEWO])\] (.+)")
    re_numof = re.compile(r"number of ([^:]*?):\s+(\d+)")

    def __init__(self, state):
        self.state = state


class FileEvent(Event):
    def slurp(self, target_file, line, line1, line2):
        # file events always start with "**["
        if not line.startswith("**["):
            return

        # forcheck changed the output format from 14.1 onwards
        if self.state.legacy_mode:
            culprit_line, fileinfo_line = line2, line1
        else:
            culprit_line, fileinfo_line = line1, line2

        # extract event code and message
        try:
            code, message = Event.re_err.match(line).groups()
        except AttributeError:
            raise ParseError("Unknown error format - " + line)

        # extract filename and line number
        try:
            filename, linenum = Event.re_file.match(fileinfo_line).groups()
        except AttributeError:  # perhaps culprit not defined and lines shifted
            match = Event.re_file.match(culprit_line)
            if match:
                filename, linenum = match.groups()
                culprit_line = ""
            else:
                filename, linenum = target_file, 0  # guess filename

        # extract details of the event
        culprit = culprit_line
        if message.startswith("("):
            # Some forcheck erros do not have specific culprits. There's no
            # consistent way to detect this, but often this occurs when
            # the event message start with "("
            culprit = ""  # assume culprit not specified

        self.state.store_file_event(filename, linenum, code, message, culprit)


class GlobalEvent(Event):
    def slurp(self, target_file, line, line1, line2):
        assert target_file is None

        # file events always start with "**["
        if not line.startswith("**["):
            return

        # extract event code and message
        try:
            code, message = Event.re_err.match(line).groups()
        except AttributeError:
            raise ParseError("Unknown error format - " + line)

        # there are cases where global events do not have an associated details
        # The only time we can detect this is when it is preceded by another
        # event.
        if line1.startswith("**["):
            details = ""
        else:
            details = line1

        self.state.store_global_event(code, message, details)


class SummaryEvent(Event):
    def slurp(self, target_file, line, line1, line2):
        assert target_file is None
        match = Event.re_summary.match(line)
        if match:
            self.validate_sums(*match.groups())
        elif line.startswith("number of "):
            self.state.store_sums(*Event.re_numof.match(line).groups())

    def validate_sums(self, count, code, message):
        if self.state._should_ignore(code):
            return
        if self.state.event_counter[code] != int(count):
            self.state.debug_required = True
            p_debug("Parsed results does not match "
                    "forcheck summary (%s)." % code)
            p_debug("  Found %d, summary states %s" %
                   (self.state.event_counter[code], count))
