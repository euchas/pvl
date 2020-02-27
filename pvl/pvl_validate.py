# -*- coding: utf-8 -*-
"""A program for testing and validating PVL text.

The ``pvl_validate`` program will read a file with PVL text (any of
the kinds of files that :func:`pvl.load` reads) and will report
on which of the various PVL dialects were able to load that PVL
text, and then also reports on whether the ``pvl`` library can encode
the Python Objects back out to PVL text.

You can imagine some PVL text that could be loaded, but is not able
to be written out in a particular strict PVL dialect (like PDS3
labels).
"""

# Copyright 2020, ``pvl`` library authors.
#
# Reuse is permitted under the terms of the license.
# The AUTHORS file and the LICENSE file are at the
# top level of this library.

import argparse
import logging
import sys
from collections import OrderedDict

import pvl
from .lexer import LexerError
from .grammar import PVLGrammar, ODLGrammar, ISISGrammar, OmniGrammar
from .parser import ParseError, PVLParser, ODLParser, OmniParser
from .decoder import PVLDecoder, ODLDecoder, OmniDecoder
from .encoder import PVLEncoder, ODLEncoder, ISISEncoder, PDSLabelEncoder

dialects = OrderedDict(PDS3=dict(parser=ODLParser(),
                                 grammar=ODLGrammar(),
                                 decoder=ODLDecoder(),
                                 encoder=PDSLabelEncoder()),
                       ODL=dict(parser=ODLParser(),
                                grammar=ODLGrammar(),
                                decoder=ODLDecoder(),
                                encoder=ODLEncoder()),
                       PVL=dict(parser=PVLParser(),
                                grammar=PVLGrammar(),
                                decoder=PVLDecoder(),
                                encoder=PVLEncoder()),
                       ISIS=dict(parser=OmniParser(),
                                 grammar=ISISGrammar(),
                                 decoder=OmniDecoder(),
                                 encoder=ISISEncoder()),
                       Omni=dict(parser=OmniParser(),
                                 grammar=OmniGrammar(),
                                 decoder=OmniDecoder(),
                                 encoder=PVLEncoder()))


def arg_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('-v', '--verbose', action='count', default=0,
                   help='Will report the errors that are encountered.')
    p.add_argument('file', nargs='+',
                   help='file containing PVL text to validate.')
    return p


def main():
    args = arg_parser().parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=(60 - 20 * args.verbose))

    results_list = list()
    for f in args.file:
        pvl_text = pvl.get_text_from(f)

        results = dict()

        for k, v in dialects.items():
            results[k] = pvl_flavor(pvl_text, k, v, f, args.verbose)

        results_list.append((f, results))

    # Writing the flavors out again to preserve order.
    print(report(results_list, list(dialects.keys())))
    return


def pvl_flavor(text, dialect, decenc: dict, filename,
               verbose=False) -> tuple((bool, bool)):
    """Returns a two-tuple of booleans which indicate
    whether the *text* could be loaded and then encoded.

    The first boolean in the two-tuple indicates whether the *text*
    could be loaded with the given parser, grammar, and decoder.
    The second indicates whether the loaded PVL object could be
    encoded with the given encoder, grammar, and decoder.  If the
    first element is False, the second will be None.
    """
    loads = None
    encodes = None
    try:
        some_pvl = pvl.loads(text, **decenc)
        loads = True

        try:
            pvl.dumps(some_pvl, **decenc)
            encodes = True
        except (LexerError, ParseError, ValueError) as err:
            logging.error(f'{dialect} encode error {filename} {err}')
            encodes = False
    except (LexerError, ParseError) as err:
        logging.error(f'{dialect} load error {filename} {err}')
        loads = False

    return (loads, encodes)


def report(reports: list, flavors: list) -> str:
    """Returns a multi-line string which is the
    pretty-printed report given the list of
    *reports*.
    """
    if len(reports[0][1]) != len(flavors):
        raise IndexError("The length of the report list keys "
                         f"({len(reports[0][1])}) "
                         "and the length of the flavors list "
                         f"({len(flavors)}) aren't the same.")

    if len(reports) > 1:
        return report_many(reports, flavors)

    r = reports[0][1]

    lines = list()
    loads = {True: 'Loads', False: 'does NOT load'}
    encodes = {True: 'Encodes', False: 'does NOT encode', None: ''}

    col1w = len(max(flavors, key=len))
    col2w = len(max(loads.values(), key=len))
    col3w = len(max(encodes.values(), key=len))

    for k in flavors:
        lines.append(build_line([k, loads[r[k][0]], encodes[r[k][1]]],
                                [col1w, col2w, col3w]))
    return '\n'.join(lines)


def report_many(r_list: list, flavors: list) -> str:
    """Returns a multi-line, table-like string which
    is the pretty-printed report of the items in *r_list*.
    """

    lines = list()
    loads = {True: 'L', False: 'No L'}
    encodes = {True: 'E', False: 'No E', None: ''}

    col1w = len(max([x[0] for x in r_list], key=len))
    col2w = len(max(loads.values(), key=len))
    col3w = len(max(encodes.values(), key=len))
    flavorw = col2w + col3w + 1

    header = ['File'] + flavors
    headerw = [col1w] + [flavorw] * len(flavors)
    rule = [' ' * col1w] + [' ' * flavorw] * len(flavors)

    rule_line = build_line(rule, headerw).replace('|', '+').replace(' ', '-')
    lines.append(rule_line)
    lines.append(build_line(header, headerw))
    lines.append(rule_line)

    for r in r_list:
        cells = [r[0]]
        widths = [col1w]
        for f in flavors:
            # cells.append(loads[r[1][f][0]] + ' ' + encodes[r[1][f][1]])
            cells.append('{0:^{w2}} {1:^{w3}}'.format(loads[r[1][f][0]],
                                                      encodes[r[1][f][1]],
                                                      w2=col2w,
                                                      w3=col3w))
            widths.append(flavorw)
        lines.append(build_line(cells, widths))

    return '\n'.join(lines)


def build_line(elements: list, widths: list, sep=' | ') -> str:
    """Returns a string formatted from the *elements* and *widths*
       provided.
    """
    cells = list()
    cells.append('{0:<{width}}'.format(elements[0], width=widths[0]))

    for e, w in zip(elements[1:], widths[1:]):
        cells.append('{0:^{width}}'.format(e, width=w))

    return sep.join(cells)


if __name__ == "__main__":
    sys.exit(main())
