# -*- coding: utf-8 -*-

import os
import re
from time import gmtime, strftime
from collections import namedtuple
from operator import itemgetter

import chardet

from jinja2 import Template
from jinja2 import Environment, PackageLoader
from pygments import highlight
from pygments.styles import get_all_styles
from pygments.formatters import HtmlFormatter

from checkfort import project_url
from checkfort.lexer import FortranLexer
from checkfort.logging import p_debug, p_verbose, p_info

jinja_env = Environment(loader=PackageLoader('checkfort', 'templates'))


def get_template(template_name):
    return jinja_env.get_template(template_name)


def render(template_name, params={}):
    return get_template(template_name).render(params)


def bytes2unicode(data):
    # search for BOM
    for bom, encoding in (('\xef\xbb\xbf', 'utf-8'),
                          ('\xff\xfe\0\0', 'utf-32'),
                          ('\0\0\xfe\xff', 'utf-32be'),
                          ('\xff\xfe', 'utf-16'),
                          ('\xfe\xff', 'utf-16be')):
        if data.startswith(bom):
            return unicode(data[len(bom):], encoding, errors='replace')

    # no BOM found, use chardet to detect encoding
    encoding = chardet.detect(data[:1024]).get('encoding') or 'utf-8'
    return unicode(data, encoding, errors='replace')


class Event(object):
    @classmethod
    def to_url(cls, code, depth=0):
        return "%sevent/%s.html" % ("../" * depth,
                                    code.replace(' ', '_'))

    def __init__(self, code, message, count):
        self.code = code
        self.message = message
        self.count = count
        self.numeric_code, self.category = code.split(None, 1)
        self.link = self.to_url(code)


class ResultWriter(object):
    def __init__(self, parser_state, outdir,
                 line_numbers=True,
                 formatter_style='default'):
        self.state = parser_state  # expect parser.ParserState instance
        self.outdir = outdir
        self.line_numbers = line_numbers

        self.formatter_style = formatter_style
        if not formatter_style in get_all_styles():
            raise CheckfortException("Invalid HtmlFormatter style - " + style)

        # vars to supply to all HTML templates
        self.default_context = {
            "to_root": "",
            "gen_date": strftime("%a, %d %b %Y %H:%M:%S", gmtime()),
            "project_url": project_url,
        }

        # default args for pygments.formatters.HtmlFormatter
        self.fmt_args = {
            "lineanchors": "line",
            "cssclass": "highlight",
            "style": formatter_style,
        }
        if self.line_numbers:
            self.fmt_args["linenos"] = "inline"

        # cache Event instances
        self.events = [
            Event(code, self.state.event_message[code], count)
            for code, count in sorted(self.state.event_counter.iteritems(),
                                      key=itemgetter(1), reverse=True)]

    def run(self):
        p_info("\nWriting HTML output to '%s'" % self.outdir)
        if self.outdir and not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)

        self._gen_assets()
        self._gen_event_pages()
        self._gen_source_pages()
        self._gen_index()

    def _gen_assets(self):
        outfile = os.path.join(self.outdir, "style.css")
        p_info(" - Generating %s" % outfile)
        with open(outfile, 'w') as f:
            f.write(render("style.css"))
            f.write(HtmlFormatter(**self.fmt_args).get_style_defs())

    def _gen_index(self):
        outfile = os.path.join(self.outdir, "index.html")
        p_info(" - Generating %s" % outfile)

        ctx = self.default_context.copy()
        ctx["event_summary"] = self.events
        with open(outfile, 'w') as f:
            f.write(render("index.html", ctx))

    def _gen_event_pages(self):
        depth = 1
        eventdir = os.path.join(self.outdir, "event")
        p_info(" - Generating event summaries")

        if not os.path.isdir(eventdir):
            os.makedirs(eventdir)

        ctx = self.default_context.copy()
        ctx["to_root"] = "../" * depth
        for e in self.events:
            outfile = "%s/%s.html" % (eventdir, e.code.replace(' ', '_'))
            ctx["event"] = e
            ctx["event_instances"] = self.state.event_instances[e.code]
            with open(outfile, 'w') as f:
                f.write(render("event.html", ctx))

    def _gen_source_pages(self):
        p_info(" - Generating marked-up source files")
        ctx = self.default_context.copy()
        for filename, event_instances in self.state.file_events.iteritems():
            ctx["code_block"], subpath, depth = self._format_source(filename)
            outfile = os.path.join(self.outdir, subpath)
            p_verbose("   -- %s" % outfile)

            ctx["to_root"] = "../" * depth
            ctx["filename"] = filename
            outdir = os.path.dirname(outfile)
            if outdir and not os.path.isdir(outdir):
                os.makedirs(outdir)

            with open(outfile, 'w') as f:
                f.write(render("code_source.html", ctx).encode('utf-8'))

    def _format_source(self, filename):
        """returns (formatted_code, target_filename, depth)"""
        outfile = os.path.join("src", "%s.html" % filename.replace(' ', '_'))
        depth = outfile.count('/')
        to_root = "../" * depth
        # get HTML formatted source as list of lines
        with open(filename, 'r') as f:
            lexer = FortranLexer(stripnl=False)
            formatter = HtmlFormatter(**self.fmt_args)
            lines = re.findall(r'<a name="line-\d+"></a>.*\n',
                               highlight(bytes2unicode(f.read()),
                                         lexer, formatter))

        # append events to target lines
        for e in self.state.file_events[filename]:
            lines[e.linenum - 1] += (
                "<span class='e-line'>  "
                "<a href='%s' class='e-link'>[%s]</a> "
                "<span class='e-label'>%s</span>: "
                "<span class='e-message'>%s</span>"
                "</span>\n" % (Event.to_url(e.code, depth),
                               e.code.rjust(5), e.culprit,
                               self.state.event_message[e.code]))

        return ("".join(lines), outfile, depth)
