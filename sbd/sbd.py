# -*- coding: utf-8 -*-
"""Parser for Iridium SBD messages"""

import collections

class Message():
    """Represents an Iridium SBD message as a raw byte sequence."""
    def __init__(self, content):
        self.content = content
        self.offset = 0

    def __str__(self):
        return str(self.content)

    def __len__(self):
        return len(self.content)

    def __getitem__(self, item):
        """
            Avoids to convert to string when requesting only 1 item,
              like msg[0]
        """
        if (isinstance(item, int) and (item != -1)):
            item = slice(item, item+1)
        return self.content[self.offset:][item]


_message_types = {
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

    Iridium transmit SBD messages through DirectIP using its own binary format.
    This class gives a comprehensible object.

    Attributes:
        header: A dictionary with the section header of an ISBD message.
        payload: A dictionary with the section payload of an ISBD message.
        confirmation: A dictionary with the section confirmation of an ISBD
            message.
        mtype: Message type, MO or MT.

    One can run this as:

    >>> isbd = IridiumSBD(msg)
    >>> isbd.header # {'IEI': ..., 'length': ...}
    >>> isbd.payload
    >>> isbd.confirmation

    >>> isbd.mtype # 'MO' | 'MT'

    >>> isbd.decode() # Parse the binary message
    >>> isbd.encode() # Encode proprieties into a binary message
    """
    def __init__(self, msg=None):
        """Initialize an IridiumSBD object.

        Args:
            msg (byte): A binary ISBD message (optional). If given, runs
                load(msg).
        """
        self.mtype = None
        if msg is not None:
            self.load(msg)

    def __str__(self):
        return str(self.attributes)

    def load(self, msg):
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
        self.msg = Message(msg)

        self.attributes = {'header': collections.OrderedDict()}
        raw = bytes(self.msg[:])

        if self.msg[0] != b'\x01':
            print(f'Message type: 0x{raw[0]:x}')
            assert False, 'Unknown message type'

        print('Parsing MO encrypted position message...')
        print(f'Iridium Edge Solar Message header: 0b{raw[1]:b}')

        message_type = _message_types[raw[1] & 0b00011111]
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
    msg = IridiumSBD(file.read())

    print('Header section:')
    for value in msg.attributes['header']:
        print(f'  - {value}: {msg.attributes["header"][value]}')
