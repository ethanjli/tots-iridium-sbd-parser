#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Command line utilities for sbd package"""

import argparse

from .parse import dump


def main():
    """Utilities for Iridium message parsing."""
    parser = argparse.ArgumentParser(
        prog='sbd',
        description='Parse an Iridium SBD MO postion message',
    )
    parser.add_argument('filename')
    args = parser.parse_args()
    with open(args.filename, 'rb') as file:
        return dump(file)


if __name__ == '__main__':
    main()
