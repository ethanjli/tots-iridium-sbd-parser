# -*- coding: utf-8 -*-
"""Parser for Iridium SBD messages"""

import binascii
import collections

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
    0x4a: 'nack',
}

_solar_edge_message_types = {
    0x00: 'radio-silence-in',
    0x01: 'radio-silence-out',
    0x03: 'start-motion',
    0x04: 'stop-motion',
    0x05: 'in-motion',
    0x14: 'null-gps',
    0x17: 'user-position-message',
    0x1b: 'position',
}

class IridiumSBD():
    """Parses an Iridium SBD messge.

    Attributes:
        header: A dictionary with the section header of an ISBD message.
    """
    def __init__(self, msg=None):
        """Initialize an IridiumSBD object.

        Args:
            msg (byte): A binary ISBD message (optional). If given, runs
                load(msg).
        """
        if msg is not None:
            self.load(msg)

    def __str__(self):
        return str(self.attributes)

    def load(self, raw):
        """Parse an Iridium SBD binary message.

        Args:
            msg (byte): A binary ISBD message (optional). If given, runs
                load(msg).

        The input (msg) is the Iridium SBD message in its original
            binary format.

        Big endian
        Protocol Revision: 1
        Data segmented into information elements (IEs)
                IEI ID      1
                IEI length  2 (content length, i.e. after the 3 initial bytes)
                IEI content N
        Information Elements Identifiers (IEI)
                MO Header IEI                 0x01
                MO Payload IEI                0x02
                MO Location Information IEI   0x03
                MO Confirmation IEI           0x05

        What is the syntax for the MO Receipt Confirmation???
        """
        self.attributes = {'header': collections.OrderedDict()}

        message_type =  _sbd_mo_message_types[raw[0]]
        self.attributes['message-type'] = message_type

        self.header = raw[1]

        message_type = _solar_edge_message_types[raw[1] & 0b00011111]
        self.attributes['header']['message-type'] = message_type
        if message_type == 'radio-silence-in':
            self.attributes['header']['message-count'] = (raw[1] & 0b11000000) >> 6
            assert (raw[1] & (0b1 << 5)) >> 5 == 1, 'bit 5 of message header has unexpected value'
            return
        if message_type == 'radio-silence-out':
            self.attributes['header']['message-count'] = (raw[1] & 0b11000000) >> 6
            self.attributes['header']['gps-fix'] = (
                '3D' if bool((raw[1] & (0b1 << 5)) >> 5) else '2D'
            )
            return
        if message_type in ('start-motion', 'stop-motion', 'in-motion'):
            self.attributes['header']['message-count'] = (raw[1] & 0b11000000) >> 6
            self.attributes['header']['gps-fix'] = (
                '3D' if bool((raw[1] & (0b1 << 5)) >> 5) else '2D'
            )
            return
        if message_type == 'null-gps':
            self.attributes['header']['powersave-mode'] = bool((raw[1] & (0b1 << 5)) >> 5)
        if message_type == 'user-position':
            self.attributes['header']['message-count'] = (raw[1] & 0b11000000) >> 6
            self.attributes['header']['gps-fix'] = (
                '3D' if bool((raw[1] & (0b1 << 5)) >> 5) else '2D'
            )
        if message_type == 'position':
            self.attributes['header']['powersave-mode'] = bool((raw[1] & (0b1 << 7)) >> 7)
            self.attributes['header']['secondary-over-50%'] = bool((raw[1] & (0b1 << 6)) >> 6)
            self.attributes['header']['gps-fix'] = (
                '3D' if bool((raw[1] & (0b1 << 5)) >> 5) else '2D'
            )


def dump(file):
    """Show isbd message header as text
    """
    raw = file.read()
    print(f'Parsing MO message {binascii.hexlify(raw, " ")}...')
    msg = IridiumSBD(raw)

    print(f'message-type: {msg.attributes["message-type"]}')
    print(f'Header 0b{msg.header:b}:')
    for value in msg.attributes['header']:
        print(f'  - {value}: {msg.attributes["header"][value]}')
