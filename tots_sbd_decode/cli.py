#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Command line utilities for sbd package"""

import argparse
import binascii

from . import parse


def main():
    """Utilities for Iridium message parsing."""
    parser = argparse.ArgumentParser(
        prog='sbd',
        description='Parse an Iridium SBD MO postion message',
    )
    parser.add_argument(
        'sbd',
        type=argparse.FileType('rb'),
        help='Path of SBD file to decode',
    )
    parser.add_argument(
        '--key',
        type=argparse.FileType('r'),
        required=False,
        help='Path of plain-text hex-encoded 3DES key file for decrypting encrypted SBD message',
    )
    args = parser.parse_args()
    print(f'Decoding \'{args.sbd.name}\'', end='')
    key = None
    if args.key is not None:
        print(f' with key \'{args.key.name}\'', end='')
        key = args.key.read().strip()
        if key == '':
            key = None
        key = binascii.unhexlify(key)
    print('...')
    return parse.dump(args.sbd.read(), key)


if __name__ == '__main__':
    main()
