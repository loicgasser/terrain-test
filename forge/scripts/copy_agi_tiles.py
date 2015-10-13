# -*- coding: utf-8 -*-

from textwrap import dedent
from forge.lib.utils import copyAGITiles


# One might want to provide an extent also later on
def usage():
    print(dedent('''\
        Usage: venv/bin/python forge/script/copy_agi_tiles.py')
    '''))


def main():
    zooms = range(0, 8)
    bounds = [-180, -90, 180, 90]
    copyAGITiles(zooms, bounds)

if __name__ == '__main__':
    main()
