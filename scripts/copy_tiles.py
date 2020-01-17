# -*- coding: utf-8 -*-

from textwrap import dedent
from forge.lib.boto_conn import copyKeys


# One might want to provide an extent also later on
def usage():
    print(dedent('''\
        Usage: venv/bin/python scripts/copy_tiles.py')
    '''))


def main():
    copyKeys('1.0.0/ch.swisstopo.terrain.3d/default/20160115/4326/',
        '1.0.0/ch.swisstopo.terrain.3d/default/20190902/4326/', range(0, 14))


if __name__ == '__main__':
    main()
