# -*- coding: utf-8 -*-

import os
import sys
import getopt
from textwrap import dedent
from forge.lib.tiler import TilerManager
from forge.lib.helpers import error


def usage():
    print(dedent('''\
        Usage: venv/bin/python forge/script/tms_writer.py [-c tms.cfg|--config=tms.cfg] <command>')

        Commands:
            create:            create the tiles and write them to S3.
            stats:             provides a report containing the stats for a given TMS config
    '''))


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:', ['config='])
    except getopt.GetoptError as err:
        error(str(err), 2, usage=usage)

    config = 'tms.cfg'
    for o, a in opts:
        if o in ('-c', '--config'):
            config = a

    if not os.path.exists(config):
        error('config file does not exists', 1, usage=usage)

    if len(args) < 1:
        error('you must specify a command', 3, usage=usage)
    tiler = TilerManager(config)

    command = args[0]
    if command == 'create':
        tiler.create()
    elif command == 'stats':
        tiler.stats()
    elif command == 'statsnodb':
        tiler.statsNoDb()
    else:
        error("unknown command '%(command)s'" % {'command': command}, 4, usage=usage)


if __name__ == '__main__':
    main()
