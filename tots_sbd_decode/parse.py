# -*- coding: utf-8 -*-
"""Parser for Iridium SBD messages"""

import binascii
import collections

from . import des

# Position Messages

_sbd_mo_position_message_types = {
    'unencrypted-position',
    'encrypted-position',
    'unencrypted-chained-position',
    'encrypted-chained-position',
}

_position_message_subtypes = {
    0x00: 'radio-silence-in',
    0x01: 'radio-silence-out',
    0x03: 'start-motion',
    0x04: 'stop-motion',
    0x05: 'in-motion',
    0x14: 'null-gps',
    0x17: 'user-position-message',
    0x1b: 'position',
}

def _parse_position_message_header(message_type, raw, attributes):
    attributes['position-message-header'] = collections.OrderedDict()
    header_attributes = attributes['position-message-header']

    header = raw[0]
    header_attributes['raw-bin'] = f'0b{header:b}'
    message_subtype = _position_message_subtypes[header & 0b00011111]
    header_attributes['message-subtype'] = message_subtype

    if message_subtype == 'radio-silence-in':
        _parse_position_header_message_count(header, header_attributes)
        if (header & (0b1 << 5)) >> 5 != 1:
            print('Error: bit 5 of message header has unexpected value')
        _check_position_message_length(message_type, message_subtype, 9, raw)
    elif message_subtype == 'radio-silence-out':
        _parse_position_header_message_count(header, header_attributes)
        _parse_position_header_gps_quality(header, header_attributes)
        _check_position_message_length(message_type, message_subtype, 9, raw)
    elif message_subtype in ('start-motion', 'stop-motion', 'in-motion'):
        _parse_position_header_message_count(header, header_attributes)
        _parse_position_header_gps_quality(header, header_attributes)
        _check_position_message_length(message_type, message_subtype, 9, raw)
    elif message_subtype == 'null-gps':
        _parse_position_header_powersave_mode(header, 5, header_attributes)
        _check_position_message_length(message_type, message_subtype, 9, raw)
    elif message_subtype == 'user-position':
        _parse_position_header_message_count(header, header_attributes)
        _parse_position_header_gps_quality(header, header_attributes)
        _check_position_message_length(message_type, message_subtype, 17, raw)
    elif message_subtype == 'position':
        _parse_position_header_powersave_mode(header, 7, header_attributes)
        _parse_position_header_secondary_battery_level(header, header_attributes)
        _parse_position_header_gps_quality(header, header_attributes)
        _check_position_message_length(message_type, message_subtype, 9, raw)

    return message_subtype

def _parse_position_message_payload(message_subtype, payload, attributes):
    attributes['payload'] = collections.OrderedDict()
    payload_attributes = attributes['payload']


    payload_attributes['raw-hex'] = binascii.hexlify(payload, ' ', 2)

    if message_subtype == 'radio-silence-in':
        if payload[:6] != b'\x00\x00\x00\x00\x00\x00':
            print('Error: first six bytes of payload have unexpected value')
        payload_attributes['triggered-magnetically'] = (payload[6] & (0b1 << 7)) >> 7
    elif message_subtype == 'radio-silence-out':
        # TODO: parse latitude & longitude
        payload_attributes['triggered-magnetically'] = (payload[6] & (0b1 << 7)) >> 7
        payload_attributes['failsafe-timed-out'] = (payload[6] & (0b1 << 6)) >> 6
    elif message_subtype in ('start-motion', 'stop-motion', 'in-motion'):
        pass
    elif message_subtype == 'null-gps':
        pass
    elif message_subtype == 'user-position':
        pass
    elif message_subtype == 'position':
        pass

    return message_subtype

def _check_position_message_length(message_type, message_subtype, expected_length, raw):
    if message_type in ('unencrypted-position', 'encrypted-position'):
        if len(raw) != expected_length:
            print(f'Error: {message_subtype} message has unexpected length {len(raw)}')
        return

def _parse_position_header_message_count(header, attributes):
    attributes['message-count'] = (header & 0b11000000) >> 6

def _parse_position_header_gps_quality(header, attributes):
    attributes['gps-quality'] = (
        '3D' if bool((header & (0b1 << 5)) >> 5) else '2D'
    )

def _parse_position_header_powersave_mode(header, position, attributes):
    attributes['powersave-mode'] = bool((header & (0b1 << position)) >> position)

def _parse_position_header_secondary_battery_level(header, attributes):
    attributes['secondary-over-50%'] = bool((header & (0b1 << 6)) >> 6)

# TLV Messages

_tlv_header_types = {
    0x23: 'config-updated',
    0x4a: 'nak',
}

def _parse_tlv(raw):
    header = raw[0]
    length = raw[1]
    value = raw[2:]
    return (header, length, value)

# Encrypted Messages

_sbd_mo_encrypted_message_types = {
    0x01: 'encrypted-position',
    0x02: 'encrypted-tlv-data',
    0x38: 'encrypted-chained-position',
    0x3a: 'encrypted-engineering',
}

# All Messages

_sbd_mo_message_types = {
    0x00: 'unencrypted-position',
    0x01: 'encrypted-position',
    0x02: 'encrypted-tlv-data',
    0x1f: 'pad-tlv',
    0x23: 'config-updated',
    0x2e: 'user-data',
    0x35: 'unencrypted-tlv-data',
    0x37: 'unencrypted-chained-position',
    0x38: 'encrypted-chained-position',
    0x39: 'unencrypted-engineering',
    0x3a: 'encrypted-engineering',
    0x4a: 'nak',
}

def _check_encrypted_message_length(message_type, raw):
    if len(raw) < 8:
        print(f'Error: {message_type} message has unexpected length {len(raw)}')

def _check_message_length(message_type, raw, min_len, max_len):
    if len(raw) < min_len or len(raw) > max_len:
        print(f'Error: {message_type} message has unexpected length {len(raw)}')

class IridiumSBD():
    """Parses an Iridium SBD messge.

    Attributes:
        header: A dictionary with the section header of an ISBD message.
    """
    def __init__(self, msg=None, key=None):
        """Initialize an IridiumSBD object.

        Args:
            msg (byte): A binary ISBD message (optional). If given, runs
                load(msg).
        """
        if msg is not None:
            self.load(msg, key)

    def __str__(self):
        return str(self.attributes)

    def load(self, raw, key):
        """Parse an Iridium SBD binary message."""
        self.attributes = collections.OrderedDict()
        self.attributes['raw-hex'] = binascii.hexlify(raw, ' ', 2)

        message_type =  _sbd_mo_message_types[raw[0]]
        self.attributes['message-type'] = message_type
        if message_type in _sbd_mo_encrypted_message_types:
            _check_message_length(message_type, raw, 10, 10)
            _check_encrypted_message_length(message_type, raw[1])
        if message_type in _sbd_mo_position_message_types:
            self._parse_position_message(message_type, raw[1:], key)
        if message_type == 'config-updated':
            _check_message_length(message_type, raw, 8, 8)
            self._parse_config_updated_message(raw[1:])
        if message_type == 'user-position':
            _check_message_length(message_type, raw, 18, 18)
        if message_type == 'user-data':
            _check_message_length(message_type, raw, 7, 66)
        if message_type in ('user-data', 'unencrypted-tlv-data'):
            self._parse_tlv_data_message(raw[1:])
        if message_type in ('unencrypted-chained-position', 'encrypted-chained-position'):
            _check_message_length(message_type, raw, 18, 66)
        if message_type in ('unencrypted-engineering', 'encrypted-engineering'):
            _check_message_length(message_type, raw, 33, 33)
        if message_type == 'nak':
            _check_message_length(message_type, raw, 7, 7)
            self._parse_nak_message(raw[1:])

    def _parse_position_message(self, message_type, raw, key):
        message_subtype = _parse_position_message_header(message_type, raw, self.attributes)

        payload = raw[1:]
        if message_type in _sbd_mo_encrypted_message_types.values():
            crypto = des.triple_des(key, pad=b'0xff')
            payload = crypto.decrypt(raw[1:])

        _parse_position_message_payload(message_subtype, payload, self.attributes)

    def _parse_config_updated_message(self, raw):
        self.attributes['tlv'] = collections.OrderedDict()
        tlv_attributes = self.attributes['tlv']

        tlv_attributes['raw-bin'] = f'0b{raw:b}'
        (header, length, value) = _parse_tlv(raw[:len(raw)-3])
        if header not in _tlv_header_types or _tlv_header_types[header] != 'config-updated':
            print(f'Unexpected header type 0x{header:x}')
        tlv_attributes['type'] = _tlv_header_types[header]
        if length != 2:
            print(f'Unexpected TLV length {length}')
        tlv_attributes['length'] = length

        if len(value) != 2:
            print(f'Unexpected value length {len(value)}')
        config_command = value[0]
        tlv_attributes['value-config-command'] = config_command
        success_code = value[1]
        tlv_attributes['value-success-code'] = success_code

        self.attributes['crc'] = f'0x{raw[len(raw)-3:]:x}'
        print('TODO: check CRC against TLV value')

    def _parse_tlv_data_message(self, raw):
        self.attributes['tlv'] = collections.OrderedDict()
        tlv_attributes = self.attributes['tlv']

        tlv_attributes['raw-bin'] = f'0b{raw:b}'
        (header, length, value) = _parse_tlv(raw[:len(raw)-3])
        tlv_attributes['type'] = _tlv_header_types[header]
        tlv_attributes['length'] = length

        tlv_attributes['value-hex'] = binascii.hexlify(value, ' ', 2)

        self.attributes['crc'] = f'0x{raw[len(raw)-3:]:x}'
        print('TODO: check CRC against TLV value')

    def _parse_nak_message(self, raw):
        self.attributes['tlv'] = collections.OrderedDict()
        tlv_attributes = self.attributes['tlv']

        tlv_attributes['raw-bin'] = f'0b{raw:b}'
        (header, length, value) = _parse_tlv(raw[:len(raw)-3])
        if header not in _tlv_header_types or _tlv_header_types[header] != 'nak':
            print(f'Unexpected header type 0x{header:x}')
        tlv_attributes['type'] = _tlv_header_types[header]
        if length != 1:
            print(f'Unexpected TLV length {length}')
        tlv_attributes['length'] = length

        if len(value) != 1:
            print(f'Unexpected value length {len(value)}')
        reason = value[0]
        nak_reasons = {
            0x05: 'improperly-formatted',
        }
        if reason not in nak_reasons:
            print(f'Unexpected NAK reason 0x{reason:x}')
            tlv_attributes['value-reason'] = reason
        else:
            tlv_attributes['value-reason'] = nak_reasons[reason]

        self.attributes['crc'] = f'0x{raw[len(raw)-3:]:x}'
        print('TODO: check CRC against TLV value')


def _print_attributes(attributes, nest_level=0):
    for key, value in attributes.items():
        for _ in range(nest_level):
            print('  ', end='')
        print(f'- {key}:', end='')
        if isinstance(value, collections.OrderedDict):
            print()
            _print_attributes(value, nest_level + 1)
            continue
        print(f' {value}')


def dump(raw, key):
    """Parse and display SBD message as structured data."""
    msg = IridiumSBD(raw, key)
    _print_attributes(msg.attributes)
