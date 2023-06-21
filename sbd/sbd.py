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
        print(f'Message header: 0b{raw[1]:b}')
        self.attributes['header']['powersave-mode'] = bool((raw[1] & (0b1 << 7)) >> 7)
        self.attributes['header']['secondary-over-50%'] = bool((raw[1] & (0b1 << 6)) >> 6)
        self.attributes['header']['gps-fix'] = '3D' if bool((raw[1] & (0b1 << 5)) >> 5) else '2D'


def dump(file, imei):
    """Show isbd message header as text
    """
    msg = IridiumSBD(file.read())
    if imei:
        print(msg.attributes['header']['IMEI'])
        return

    print('Header section:')
    for value in msg.attributes['header']:
        print(f'  - {value}: {msg.attributes["header"][value]}')
