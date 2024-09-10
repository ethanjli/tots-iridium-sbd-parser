#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Command line utilities for sbd package"""

import argparse
import binascii

from . import parse


def main():
    """Utilities for Iridium message parsing."""
    parser = argparse.ArgumentParser(
        prog='tots-sbd-decode',
        description='Parse an Iridium Edge Solar SBD MO message',
    )
    parser.add_argument(
        'sbd',
        type=argparse.FileType('rb'),
        help='Path of the SBD file to decode',
    )
    parser.add_argument(
        '-k', '--key',
        type=argparse.FileType('r'),
        required=False,
        help=(
            'Path of a plain-text hex-encoded 3DES key file for decrypting the payload of an ',
            'encrypted SBD message',
        ),
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help='Print raw binary/hex encodings of parsed values',
    )
    args = parser.parse_args()
    print(f'Decoding Iridium Edge Solar SBD MO message \'{args.sbd.name}\'', end='')
    key = None
    if args.key is not None:
        print(f' with key \'{args.key.name}\'', end='')
        key = args.key.read().strip()
        if key == '':
            key = None
        key = binascii.unhexlify(key)
    print('...')
    msg = parse.IridiumSBD(args.sbd.read(), key)
    parse.print_attrs(msg.attrs, verbose=args.verbose)


if __name__ == '__main__':
    main()
