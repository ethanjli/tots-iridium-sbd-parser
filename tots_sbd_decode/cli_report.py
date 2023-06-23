#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Command line utilities for sbd package"""

import argparse
import binascii
import collections
import csv
import os
import traceback

from . import parse

_keys = {}

def _load_key_memoized(imei, keys_dir):
    if imei in _keys:
        return _keys[imei]

    key = None
    if keys_dir is not None:
        with open(os.path.join(keys_dir, f'{imei}.3des-key'), 'r', encoding='utf-8') as file:
            key = file.read().strip()
            if key == '':
                key = None
        key = binascii.unhexlify(key)
    _keys[imei] = key
    return key

def _check_record_consistency(record):
    latitude = record['latitude']
    msg_latitude = record['message']['payload']['latitude']
    if latitude[:-2] != msg_latitude[:-2]:
        print(
            f'Error: latitude decoded from message {msg_latitude} is inconsistent with '
            f'latitude {latitude} from records!',
        )

    longitude = record['longitude']
    msg_longitude = record['message']['payload']['longitude']
    if longitude[:-2] != msg_longitude[:-2]:
        print(
            f'Error: longitude decoded from message {msg_longitude} is inconsistent with '
            f'longitude {longitude} from records!',
        )

    speed = record['speed']
    msg_speed = record['message']['payload']['heading-speed']['speed'][0]
    if speed != msg_speed:
        print(
            f'Error: speed decoded from message {msg_speed} is inconsistent with '
            f'speed {speed} from records!',
        )

    heading = record['heading']
    msg_heading = record['message']['payload']['heading-speed']['heading'][0]
    if heading != msg_heading:
        print(
            f'Error: heading decoded from message {msg_heading} is inconsistent with '
            f'heading {heading} from records!',
        )

def _dump(report_record, keys_dir, verbose=False):
    print('Decoding record:', report_record)
    record = collections.OrderedDict()
    name = report_record['Asset Name']
    if name == 'Asset Name':
        # We've encountered a repeated header row which is added by MetOcean LiNC between sections
        # of a multi-device report CSV file for different devices; so we'll just silently skip this
        # row as an invalid report record
        return
    record['name'] = name
    record['imei'] = report_record['Asset Id']
    record['date-utc'] = report_record['Data Date (UTC)']
    record['latitude'] = report_record['Latitude'].replace(' \'', '\'')
    record['longitude'] = report_record['Longitude'].replace(' \'', '\'')
    record['speed'] = round(float(report_record['Speed']))
    record['heading'] = round(float(report_record['Heading']))

    imei = report_record['Asset Id']
    sbd = report_record['Report Body'].replace('-', '')
    try:
        msg = parse.IridiumSBD(binascii.unhexlify(sbd), _load_key_memoized(imei, keys_dir))
        record['message'] = msg.attrs
    except (ValueError, IndexError, KeyError):
        print('Error: couldn\'t decode record!')
        traceback.print_exc()
    parse.print_attrs(record, verbose=verbose)
    try:
        _check_record_consistency(record)
    except KeyError:
        print(
            'Error: couldn\'t check the decoded message for consistency with the record, '
            'because it\'s missing some required fields (perhaps message decoding failed?)',
        )


def main():
    """Utilities for Iridium message parsing."""
    parser = argparse.ArgumentParser(
        prog='tots-report-decode',
        description=(
            'Parse a MetOcean LiNC CSV history report of Iridium Edge Solar ',
            'SBD MO messages',
        ),
    )
    parser.add_argument(
        'report',
        type=argparse.FileType('r', encoding='latin-1'),
        help='Path of history report CSV file to decode',
    )
    parser.add_argument(
        '-K', '--keys',
        type=str,
        required=False,
        help=(
            'Path of a directory containing plain-text hex-encoded 3DES key files (with file ',
            'extension .3des-key) for decrypting encrypted SBD messages',
        ),
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help='Print raw binary/hex encodings of parsed values',
    )
    args = parser.parse_args()
    print(f'Decoding MetOcean LiNC history report \'{args.report.name}\'', end='')
    print('...')

    csv.register_dialect('metoceanlinc', skipinitialspace=True, strict=True)
    report_reader = csv.DictReader(args.report, dialect='metoceanlinc')
    for record in report_reader:
        print()
        _dump(record, args.keys, verbose=args.verbose)


if __name__ == '__main__':
    main()
