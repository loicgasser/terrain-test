# -*- coding: utf-8 -*-

from textwrap import dedent
from forge.lib.boto_conn import copyKeys


# One might want to provide an extent also later on
def usage():
    print(dedent('''\
        Usage: venv/bin/python forge/script/copy_tiles.py')
    '''))


def main():
    copyKeys('1.0.0/ch.swisstopo.terrain.3d/default/20151231/4326/',
        '1.0.0/ch.swisstopo.terrain.3d_light/default/20151231/4326/', range(0, 9))

if __name__ == '__main__':
    main()
