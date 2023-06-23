# -*- coding: utf-8 -*-
"""Parser for Iridium SBD messages"""

import binascii
import collections
import datetime
import traceback

from . import des

# Utilities

def _isolate_bits(byte, position, mask=0b1):
    return (byte & mask << position) >> position

def _hexlify(byte_or_bytes):
    if isinstance(byte_or_bytes, int):
        return _hexlify(bytes([byte_or_bytes]))
    return binascii.hexlify(byte_or_bytes, ' ', 2)

def _binify(byte_or_bytes, pad=0):
    if isinstance(byte_or_bytes, int):
        match pad:
            case 0:
                return f'0b{byte_or_bytes:b}'
            case _:
                return format(byte_or_bytes, f'#0{pad + 2}b')
    if isinstance(pad, int):
        binified = [_binify(byte, pad) for byte in byte_or_bytes]
    else:
        binified = [_binify(byte, pad) for (byte, pad) in zip(byte_or_bytes, pad)]
    return ' '.join(binified)

def _parse_bool_flag(byte, name, position, attrs):
    flag = _isolate_bits(byte, position)
    attrs[f'{name}-(bin)'] = _binify(flag, pad=1)
    attrs[f'{name}'] = bool(flag)

# Chained Locations

_time_weights = {
    0b000: datetime.timedelta(seconds=30),
    0b001: datetime.timedelta(minutes=2),
    0b010: datetime.timedelta(minutes=15),
    0b011: datetime.timedelta(hours=1),
    0b100: datetime.timedelta(hours=4),
    0b101: datetime.timedelta(hours=8),
    0b110: datetime.timedelta(hours=12),
    0b111: datetime.timedelta(hours=24),
}

def _parse_chained_location_delta_time(delta_time, delta_time_attrs):
    delta_time_attrs['(bin)'] = _binify(delta_time, pad=8)

    weight = _isolate_bits(delta_time, 5, mask=0b111)
    delta_time_attrs['(weight)-(bin)'] = _binify(weight, pad=3)
    delta_time_attrs['(weight)'] = _time_weights[weight]

    multiplier = delta_time & 0b11111
    delta_time_attrs['(multiplier)-(bin)'] = _binify(multiplier, pad=5)
    delta_time_attrs['(multiplier)'] = multiplier

    duration = multiplier * _time_weights[weight]
    delta_time_attrs['duration'] = '>31 days' if duration == 0 else duration

def _parse_chained_location_status_beta(status, status_beta_attrs):
    status_beta_attrs['(hex)'] = _hexlify(status)
    status_beta_attrs['(bin)'] = _binify(status, pad=8)
    _parse_position_heading_speed(status, status_beta_attrs)

def _parse_chained_location_status_prod(status, status_prod_attrs):
    status_prod_attrs['(hex)'] = _hexlify(status)
    status_prod_attrs['(bin)'] = _binify(status, pad=8)

    _parse_bool_flag(status, 'from-position-message', 0, status_prod_attrs)
    _parse_bool_flag(status, 'from-power-save-position-message', 1, status_prod_attrs)
    _parse_bool_flag(status, 'from-home-position-message', 2, status_prod_attrs)
    _parse_bool_flag(status, 'from-away-position-message', 3, status_prod_attrs)
    _parse_bool_flag(status, 'from-user-position-message', 4, status_prod_attrs)
    _parse_bool_flag(status, 'from-radio-silence-out-position-message', 5, status_prod_attrs)
    _parse_bool_flag(status, 'from-motion-start-message', 6, status_prod_attrs)
    _parse_bool_flag(status, 'from-motion-stop-message', 7, status_prod_attrs)
    _parse_bool_flag(status, 'from-in-motion-message', 8, status_prod_attrs)

    speed = status & 0b1111
    status_prod_attrs['speed-(bin)'] = _binify(speed, pad=4)
    status_prod_attrs['speed'] = (speed * 8, 'mph')

def _parse_chained_location(chained_location, chained_location_attrs):
    chained_location_attrs['(hex)'] = _hexlify(chained_location)

    delta_time_attrs = collections.OrderedDict()
    chained_location_attrs['chain-delta-time'] = delta_time_attrs
    _parse_chained_location_delta_time(chained_location[0], delta_time_attrs)

    _parse_position_lat_long(chained_location[1:7], chained_location_attrs)

    status_beta_attrs = collections.OrderedDict()
    chained_location_attrs['status-beta'] = status_beta_attrs
    _parse_chained_location_status_beta(chained_location[7], status_beta_attrs)

    status_prod_attrs = collections.OrderedDict()
    chained_location_attrs['status-prod'] = status_prod_attrs
    _parse_chained_location_status_prod(chained_location[7], status_prod_attrs)

def _parse_position_msg_chain(payload_chained, payload_chained_attrs):
    payload_chained_attrs['(hex)'] = _hexlify(payload_chained)
    if len(payload_chained) % 8 != 0:
        print(f'Warning: chained positions have unexpected total length of {len(payload_chained)}!')
    for i in range(0, len(payload_chained), 8):
        chained_location_attrs = collections.OrderedDict()
        payload_chained_attrs[f'{i // 8}'] = chained_location_attrs
        _parse_chained_location(payload_chained[i:i+8], chained_location_attrs)

# Position Messages

_position_msg_subtypes = {
    0x00: 'radio-silence-in',
    0x01: 'radio-silence-out',
    0x03: 'start-motion',
    0x04: 'stop-motion',
    0x05: 'in-motion',
    0x14: 'null-gps',
    0x17: 'user-position-message',
    0x1b: 'position',
}

def _parse_position_msg_header(header, header_attrs):
    header_attrs['(hex)'] = _hexlify(header)
    header_attrs['(bin)'] = _binify(header, pad=8)

    raw_subtype = header & 0b11111
    if raw_subtype not in _position_msg_subtypes:
        print(f'Error: unexpected message subtype 0x{raw_subtype:x}!')
        return None

    msg_subtype = _position_msg_subtypes[raw_subtype]
    match msg_subtype:
        case 'radio-silence-in':
            _parse_position_header_msg_count(header, header_attrs)
            header_attrs['(unused)-(bin)'] = _binify(_isolate_bits(header, 5), pad=1)
            if _isolate_bits(header, 5) != 1:
                print('Error: bit 5 of message header has unexpected value!')
        case 'radio-silence-out':
            _parse_position_header_msg_count(header, header_attrs)
            _parse_position_header_gps_quality(header, header_attrs)
        case 'start-motion' | 'stop-motion' | 'in-motion':
            _parse_position_header_msg_count(header, header_attrs)
            _parse_position_header_gps_quality(header, header_attrs)
        case 'null-gps':
            header_attrs['(unused)-(bin)'] = \
                _binify(_isolate_bits(header, 6, mask=0b11), pad=2)
            if _isolate_bits(header, 5) != 1:
                print('Error: bit 5 of message header has unexpected value!')
            _parse_bool_flag(header, 'powersave-mode', 5, header_attrs)
        case 'user-position':
            _parse_position_header_msg_count(header, header_attrs)
            _parse_position_header_gps_quality(header, header_attrs)
        case 'position':
            _parse_bool_flag(header, 'powersave-mode', 7, header_attrs)
            _parse_bool_flag(header, 'secondary-over-50%', 6, header_attrs)
            _parse_position_header_gps_quality(header, header_attrs)
        case _:
            print(f'Error: unexpected message subtype {msg_subtype}!')

    header_attrs['message-subtype-(bin)'] = _binify(raw_subtype, pad=5)
    header_attrs['message-subtype-(hex)'] = _hexlify(raw_subtype)
    header_attrs['message-subtype'] = msg_subtype

    return msg_subtype

def _parse_position_header_msg_count(header, header_attrs):
    msg_count = _isolate_bits(header, 6, mask=0b11)
    header_attrs['message-count-(bin)'] = _binify(msg_count, pad=2)
    header_attrs['message-count'] = msg_count

_gps_quality_values = {
    True: '3D',
    False: '2D',
}

def _parse_position_header_gps_quality(header, header_attrs):
    gps_quality = bool(_isolate_bits(header, 5))
    header_attrs['gps-quality-(bin)'] = _binify(gps_quality, pad=1)
    header_attrs['gps-quality'] = _gps_quality_values[gps_quality]

def _parse_position_radio_msg_status(msg_subtype, status, status_attrs):
    status_attrs['(hex)'] = _hexlify(status)
    status_attrs['(bin)'] = _binify(status, pad=8)
    _parse_bool_flag(status[0], 'triggered-magnetically', 7, status_attrs)
    match msg_subtype:
        case 'radio-silence-in':
            status_attrs['(unused)'] = _binify(_isolate_bits(status[0], 6), pad=1)
            status_attrs['(future)-(bin)'] = \
                _binify(((status[0] & 0b111111), status[1]), pad=(6, 8))
        case 'radio-silence-out':
            _parse_bool_flag(status[0], 'failsafe-timed-out', 6, status_attrs)
            status_attrs['(reserved)-(bin)'] =\
                _binify(((status[0] & 0b111111), status[1]), pad=(6, 8))
        case _:
            print(f'Error: unexpected message subtype 0x{msg_subtype:x}!')

def _parse_timestamp(raw, timestamp_attrs):
    timestamp_attrs['(hex)'] = _hexlify(raw)
    parsed = int.from_bytes(raw, 'big', signed=False)
    timestamp_attrs['int'] = parsed
    timestamp_attrs['local'] = datetime.datetime.fromtimestamp(parsed)
    timestamp_attrs['utc'] = datetime.datetime.utcfromtimestamp(parsed)

_position_msg_status_modes = {
    0: '(reserved)',
    1: 'standard-interval',
    2: 'home-mode',
    3: 'away-mode',
    4: 'power-save-mode',
    5: 'user-mode',
}

def _parse_position_msg_position_status(status, status_attrs):
    status_attrs['(hex)'] = _hexlify(status)
    status_attrs['(bin)'] = _binify(status, pad=8)

    _parse_bool_flag(status, 'vibration-motion', 7, status_attrs)
    mode = _isolate_bits(status, 4, mask=0b111)
    status_attrs['mode-(bin)'] = _binify(mode, pad=3)
    status_attrs['mode-(int)'] = mode
    if mode not in _position_msg_status_modes:
        print(f'Error: position message status mode has unexpected value {mode}!')
    else:
        status_attrs['mode'] = _position_msg_status_modes[mode]
    status_attrs['(reserved)'] = _binify(status & 0b111, pad=3)

def _convert_dec_to_dm(dd):
    # Adapted from https://stackoverflow.com/a/12737895, which is licensed under CC-BY-SA-3.0
    negative = dd < 0
    dd = abs(dd)
    degrees, minutes = divmod(dd * 60, 60)
    if not negative:
        return (round(degrees), round(minutes, 5))
    if degrees > 0:
        return (round(-degrees), round(minutes, 5))
    return (round(degrees), round(-minutes, 5))

def _parse_position_lat_long(payload_lat_long, payload_attrs):
    lat = payload_lat_long[0:3]
    payload_attrs['latitude-(hex)'] = _hexlify(lat)
    lat_encoded = int.from_bytes(lat, 'big', signed=False)
    threshold = 2 ** 23 / 90
    lat_dec = (
        -1 * (180 - lat_encoded / threshold) if lat_encoded / threshold > 90
        else lat_encoded / threshold
    )
    payload_attrs['latitude-(decimal)'] = (lat_dec, '°')
    lat_deg, lat_min = _convert_dec_to_dm(lat_dec)
    payload_attrs['latitude'] = (f'{lat_deg}° {lat_min:.05f}\'')

    long = payload_lat_long[3:6]
    payload_attrs['longitude-(hex)'] = _hexlify(long)
    long_encoded = int.from_bytes(long, 'big', signed=False)
    threshold = 2 ** 23 / 180
    long_dec = (
        -1 * (360 - long_encoded / threshold) if long_encoded / threshold > 180
        else long_encoded / threshold
    )
    payload_attrs['longitude-(decimal)'] = (long_dec, '°')
    long_deg, long_min = _convert_dec_to_dm(long_dec)
    payload_attrs['longitude'] = (f'{long_deg}° {long_min:.05f}\'')

def _parse_position_heading_speed(payload_heading_speed, payload_heading_speed_attrs):
    payload_heading_speed_attrs['(hex)'] = _hexlify(payload_heading_speed)
    payload_heading_speed_attrs['(bin)'] = _binify(payload_heading_speed, pad=8)

    heading = _isolate_bits(payload_heading_speed, 5, mask=0b111)
    payload_heading_speed_attrs['heading-(bin)'] = _binify(heading, pad=3)
    payload_heading_speed_attrs['heading'] = (heading * 45, '°')

    speed = payload_heading_speed & 0b11111
    payload_heading_speed_attrs['speed-(bin)'] = _binify(speed, pad=5)
    payload_heading_speed_attrs['speed'] = (speed * 4, 'mph')

def _parse_position_msg_motion_payload(payload, payload_attrs):
    _parse_position_lat_long(payload[0:6], payload_attrs)
    time_of_day = payload[6]
    payload_attrs['time-of-day-(hex)'] = _hexlify(time_of_day)
    if time_of_day > (60 * 24) / 6:
        print(f'Error: unexpectedly large time-of-day {time_of_day}')
    payload_attrs['time-of-day-(min)'] = time_of_day * 6
    hours, minutes = divmod(time_of_day * 6, 60)
    payload_attrs['time-of-day'] = f'{hours:02d}:{minutes:02d}'

    heading_speed_attrs = collections.OrderedDict()
    payload_attrs['heading-speed'] = heading_speed_attrs
    _parse_position_heading_speed(payload[7], heading_speed_attrs)

def _parse_position_msg_null_gps_payload(payload, payload_attrs):
    if payload[:2] != b'\xff\xff':
        print('Error: first two bytes of payload have unexpected value!')
    payload_attrs['(unused-1)'] = payload[:2]
    payload_attrs['failing-message-event-id'] = _hexlify(payload[2])
    if payload[3] != b'\xff':
        print('Error: fourth byte of payload has unexpected value!')
    payload_attrs['(unused-2)'] = payload[3]
    payload_attrs['gps-failed-search-duration'] = (payload[4], 's')
    payload_attrs['gps-failed-count'] = payload[5]
    payload_attrs['failing-message-event-last-bytes'] = _hexlify(payload[6:8])

def _parse_position_msg_position_payload(payload, payload_attrs):
    _parse_position_lat_long(payload[0:6], payload_attrs)

    status_attrs = collections.OrderedDict()
    payload_attrs['status'] = status_attrs
    _parse_position_msg_position_status(payload[6], status_attrs)

    heading_speed_attrs = collections.OrderedDict()
    payload_attrs['heading-speed'] = heading_speed_attrs
    _parse_position_heading_speed(payload[7], heading_speed_attrs)

def _parse_position_msg_payload(msg_type, msg_subtype, payload, payload_attrs):
    match msg_subtype:
        case 'radio-silence-in':
            if payload[:6] != b'\x00\x00\x00\x00\x00\x00':
                print('Error: first six bytes of payload have unexpected value!')
            payload_attrs['(unused)'] = _hexlify(payload[:6])

            status_attrs = collections.OrderedDict()
            payload_attrs['status'] = status_attrs
            _parse_position_radio_msg_status(msg_subtype, payload[6:8], status_attrs)
        case 'radio-silence-out':
            _parse_position_lat_long(payload[0:6], payload_attrs)

            status_attrs = collections.OrderedDict()
            payload_attrs['status'] = status_attrs
            _parse_position_radio_msg_status(msg_subtype, payload[6:8], status_attrs)
        case 'start-motion' | 'stop-motion' | 'in-motion':
            _parse_position_msg_motion_payload(payload, payload_attrs)
        case 'null-gps':
            _parse_position_msg_null_gps_payload(payload, payload_attrs)
        case 'user-position':
            _parse_position_lat_long(payload[0:6], payload_attrs)
            payload_attrs['user-data'] = _hexlify(payload[6:12])

            timestamp_attrs = collections.OrderedDict()
            payload_attrs['timestamp'] = timestamp_attrs
            _parse_timestamp(payload[12:16], timestamp_attrs)
        case 'position':
            _parse_position_msg_position_payload(payload, payload_attrs)

    if msg_type not in ('unencrypted-chained-position', 'encrypted-chained-position'):
        return

    payload_chained_attrs = collections.OrderedDict()
    payload_attrs['chained-locations'] = payload_chained_attrs
    _parse_position_msg_chain(
        payload[16:] if msg_subtype == 'user_position' else payload[8:],
        payload_chained_attrs,
    )

def _check_position_msg_length(msg_type, msg_subtype, expected_length, raw):
    if msg_type not in ('unencrypted-position', 'encrypted-position'):
        return

    if len(raw) != expected_length:
        print(f'Error: {msg_subtype} message has unexpected length {len(raw)}!')

# TLV Messages

_tlv_header_types = {
    0x1f: 'pad-tlv',
    0x23: 'config-updated',
    0x2e: 'user-data',
    0x4a: 'nak',
}

def _parse_tlv(raw):
    header = raw[0]
    length = raw[1]
    value = raw[2:]
    return (header, length, value)

_nak_reasons = {
    0x05: 'improperly-formatted',
}

def _parse_config_updated_tlv(length, value, tlv_attrs):
    if length != 2:
        print(f'Error: unexpected TLV length {length}!')

    config_command = value[0]
    tlv_attrs['value-config-command-(hex)'] = _hexlify(config_command)
    tlv_attrs['value-config-command'] = config_command
    success_code = value[1]
    tlv_attrs['value-success-code-(hex)'] = _hexlify(success_code)
    tlv_attrs['value-success-code'] = success_code

def _parse_nak_tlv(length, value, tlv_attrs):
    if length != 1:
        print(f'Error: unexpected TLV length {length}!')

    reason = value[0]
    tlv_attrs['value-reason-(hex)'] = _hexlify(reason)
    if reason not in _nak_reasons:
        print(f'Error: unexpected NAK reason 0x{reason:x}')
    else:
        tlv_attrs['value-reason'] = _nak_reasons[reason]

# Engineering Messages

_eng_last_reset_types = {
    0x00: 'first-boot',
    0x01: 'hw-watchdog-reset',
    0x02: 'sw-watchdog-reset',
    0x03: 'sw-reset',
    0x04: 'cpu-lock-reset',
    0x05: 'power-detect-reset',
    0x09: 'power-on-reset',
}

def _parse_eng_msg_payload_gps(payload_gps, payload_gps_attrs):
    payload_gps_attrs['(hex)'] = _hexlify(payload_gps)
    payload_gps_attrs['(bin)'] = _binify(payload_gps, pad=8)

    failure_ratio = payload_gps[0] & 0b111111
    payload_gps_attrs['failure-ratio-(bin)'] = _binify(failure_ratio, pad=6)
    payload_gps_attrs['failure-ratio'] = (failure_ratio * 1.5, '%')

    mean_fix_time = payload_gps[1]
    payload_gps_attrs['mean-search-time-(hex)'] = _hexlify(mean_fix_time)
    payload_gps_attrs['mean-search-time'] = (mean_fix_time, 's')

    mean_sv_num_per_fix = payload_gps[2]
    payload_gps_attrs['mean-satellites-per-fix-(hex)'] = _hexlify(mean_sv_num_per_fix)
    payload_gps_attrs['mean-satellites-per-fix'] = mean_sv_num_per_fix

    mean_hdop = payload_gps[3]
    payload_gps_attrs['mean-horizontal-dilution-of-precision-(hex)'] = _hexlify(mean_hdop)
    payload_gps_attrs['mean-horizontal-dilution-of-precision'] = mean_hdop

def _parse_eng_msg_payload_iridium(payload_iridium, payload_iridium_attrs):
    payload_iridium_attrs['(hex)'] = _hexlify(payload_iridium)
    payload_iridium_attrs['(bin)'] = _binify(payload_iridium, pad=8)

    acq_failure_ratio = _isolate_bits(payload_iridium[0], 4, mask=0b1111)
    payload_iridium_attrs['acq-failure-ratio-(bin)'] = _binify(acq_failure_ratio, pad=3)
    payload_iridium_attrs['acq-failure-ratio'] = (acq_failure_ratio * 6.7, '%')

    ts_net_failure_ratio = _isolate_bits(payload_iridium[0], 4, mask=0b1111)
    payload_iridium_attrs['ts/network-failure-ratio-(bin)'] = _binify(ts_net_failure_ratio, pad=3)
    payload_iridium_attrs['ts/network-failure-ratio'] = (ts_net_failure_ratio * 6.7, '%')

    transmit_attempts = payload_iridium[1:3]
    payload_iridium_attrs['transmit-attempts-(hex)'] = _hexlify(transmit_attempts)
    payload_iridium_attrs['transmit-attempts'] = int.from_bytes(
        transmit_attempts, 'big', signed=False,
    )

    mean_acq_time = payload_iridium[3]
    payload_iridium_attrs['mean-acq-time-(hex)'] = _hexlify(mean_acq_time)
    payload_iridium_attrs['mean-acq-time'] = (mean_acq_time, 's')

    mean_tx_time = payload_iridium[4]
    payload_iridium_attrs['mean-tx-time-(hex)'] = _hexlify(mean_tx_time)
    payload_iridium_attrs['mean-tx-time'] = (mean_tx_time, 's')

    mean_tx_rssi = payload_iridium[5]
    payload_iridium_attrs['mean-rssi-at-tx-(hex)'] = _hexlify(mean_tx_rssi)
    payload_iridium_attrs['mean-rssi-at-tx'] = mean_tx_rssi * 100

def _parse_eng_msg_payload_battery(payload_battery, payload_battery_attrs):
    payload_battery_attrs['(hex)'] = _hexlify(payload_battery)

    primary_charge = payload_battery[0]
    payload_battery_attrs['primary-charge-(hex)'] = _hexlify(primary_charge)
    payload_battery_attrs['primary-charge'] = (primary_charge, '%')

    secondary_charge = payload_battery[1]
    payload_battery_attrs['secondary-charge-(hex)'] = _hexlify(secondary_charge)
    payload_battery_attrs['secondary-charge'] = (secondary_charge, '%')

    secondary_surplus_deficit = payload_battery[2]
    payload_battery_attrs['secondary-surplus/deficit-(hex)'] = _hexlify(secondary_surplus_deficit)
    payload_battery_attrs['secondary-surplus/deficit'] = (
        int.from_bytes(secondary_surplus_deficit, 'big', signed=True),
        '%',
    )

    secondary_usage_time = payload_battery[3]
    payload_battery_attrs['secondary-usage-time-(hex)'] = _hexlify(secondary_usage_time)
    payload_battery_attrs['secondary-usage-time'] = (secondary_usage_time, '%')

def _parse_eng_msg_payload_temperature(payload_temperature, payload_temperature_attrs):
    payload_temperature_attrs['(hex)'] = _hexlify(payload_temperature)

    max_since_prev = payload_temperature[0]
    payload_temperature_attrs['max-since-prev-eng-msg-(hex)'] = _hexlify(max_since_prev)
    payload_temperature_attrs['max-since-prev-eng-msg'] = (max_since_prev, '°C')

    min_since_prev = payload_temperature[1]
    payload_temperature_attrs['min-since-prev-eng-msg-(hex)'] = _hexlify(min_since_prev)
    payload_temperature_attrs['min-since-prev-eng-msg'] = (min_since_prev, '°C')

    mean_since_prev = payload_temperature[2]
    payload_temperature_attrs['mean-since-prev-eng-msg-(hex)'] = _hexlify(mean_since_prev)
    payload_temperature_attrs['mean-since-prev-eng-msg'] = (mean_since_prev, '°C')

def _parse_twos_complement(value, width):
    if (value & (1 << (width - 1))) != 0:
        value = value - (1 << width)
    return value

def _parse_eng_msg_payload_acceleration(payload_acceleration, payload_acceleration_attrs):
    payload_acceleration_attrs['(hex)'] = _hexlify(payload_acceleration)
    payload_acceleration_attrs['(bin)'] = _binify(payload_acceleration, pad=8)

    acc_x = _isolate_bits(payload_acceleration[0], 4, mask=0b1111)
    payload_acceleration_attrs['x-(bin)'] = _binify(acc_x, pad=4)
    payload_acceleration_attrs['x'] = (_parse_twos_complement(acc_x, 4) * 0.25, 'g')

    acc_y = payload_acceleration[0] & 0b1111
    payload_acceleration_attrs['y-(bin)'] = _binify(acc_y, pad=4)
    payload_acceleration_attrs['y'] = (_parse_twos_complement(acc_y, 4) * 0.25, 'g')

    acc_z = _isolate_bits(payload_acceleration[1], 4, mask=0b111)
    payload_acceleration_attrs['z-(bin)'] = _binify(acc_z, pad=4)
    payload_acceleration_attrs['z'] = (_parse_twos_complement(acc_z, 4) * 0.25, 'g')

    reserved = bytes([payload_acceleration[1] & 0b111, payload_acceleration[2]])
    payload_acceleration_attrs['(reserved)-(bin)'] = _binify(reserved, pad=(4, 8))

def _parse_eng_msg_payload(payload, payload_attrs):
    config_change_counter = _isolate_bits(payload[0], 6, mask=0b11)
    payload_attrs['config-change-counter-(bin)'] = _binify(config_change_counter, pad=2)
    payload_attrs['config-change-counter'] = config_change_counter

    payload_gps_attrs = collections.OrderedDict()
    payload_attrs['gps'] = payload_gps_attrs
    _parse_eng_msg_payload_gps(payload[0:4], payload_gps_attrs)

    powersave_ratio = _isolate_bits(payload[4], 4, mask=0b111)
    payload_attrs['powersave-ratio-(bin)'] = _binify(powersave_ratio, pad=3)
    payload_attrs['powersave-ratio'] = (powersave_ratio * 6.7, '%')

    last_reset_type = _isolate_bits(payload[4], 0, mask=0b1111)
    payload_attrs['last-reset-type-(bin)'] = _binify(last_reset_type, pad=4)
    payload_attrs['last-reset-type-(hex)'] = _hexlify(last_reset_type)
    if last_reset_type not in _eng_last_reset_types:
        print(f'Error: unknown last reset type 0x{last_reset_type:x}!')
    else:
        payload_attrs['last-reset-type'] = _eng_last_reset_types[last_reset_type]

    payload_iridium_attrs = collections.OrderedDict()
    payload_attrs['iridium'] = payload_iridium_attrs
    _parse_eng_msg_payload_iridium(payload[5:11], payload_iridium_attrs)

    payload_battery_attrs = collections.OrderedDict()
    payload_attrs['battery'] = payload_battery_attrs
    _parse_eng_msg_payload_battery(payload[11:15], payload_battery_attrs)

    reserved = payload[15:20]
    payload_attrs['(reserved)-(hex)'] = _hexlify(reserved)

    payload_temperature_attrs = collections.OrderedDict()
    payload_attrs['temperature'] = payload_temperature_attrs
    _parse_eng_msg_payload_temperature(payload[20:23], payload_temperature_attrs)

    payload_acceleration_attrs = collections.OrderedDict()
    payload_attrs['acceleration'] = payload_acceleration_attrs
    _parse_eng_msg_payload_acceleration(payload[23:26], payload_acceleration_attrs)

    mean_lux = payload[26:28]
    payload_attrs['mean-light-intensity-(hex)'] = _hexlify(mean_lux)
    payload_attrs['mean-light-intensity'] = (
        int.from_bytes(mean_lux, 'big', signed=False),
        'lux',
    )

    current_lux_ratio = payload[28]
    payload_attrs['mean-charge-current-mean-light-intensity-ratio-(hex)'] = \
        _hexlify(current_lux_ratio)
    payload_attrs['mean-charge-current-mean-light-intensity-ratio'] = (current_lux_ratio, 'mA/lux')

    system_status = payload[29:33]
    payload_attrs['system-status-(hex)'] = _hexlify(system_status)
    payload_attrs['system-status-(bin)'] = _binify(system_status, pad=8)

# Encrypted Messages

_sbd_mo_encrypted_msg_types = {
    0x01: 'encrypted-position',
    0x02: 'encrypted-tlv-data',
    0x38: 'encrypted-chained-position',
    0x3a: 'encrypted-engineering',
}

def _decrypt_payload(msg_type, payload, key, payload_attrs):
    if msg_type not in _sbd_mo_encrypted_msg_types.values():
        return payload

    payload_attrs['(ciphertext)-(hex)'] = _hexlify(payload)
    if key is None or key == '':
        print('Warning: missing a key to decrypt the payload!')
        return None
    crypto = des.triple_des(key, pad=b'0xff')
    try:
        return crypto.decrypt(payload)
    except ValueError as err:
        print('Error: couldn\'t decrypt payload')
        traceback.print_exc()
        return None

# All Messages

_sbd_mo_msg_types = {
    0x00: 'unencrypted-position',
    0x01: 'encrypted-position',
    0x02: 'encrypted-tlv-data',
    0x35: 'unencrypted-tlv-data',
    0x37: 'unencrypted-chained-position',
    0x38: 'encrypted-chained-position',
    0x39: 'unencrypted-engineering',
    0x3a: 'encrypted-engineering',
}

def _check_msg_length(msg_type, raw, min_len, max_len):
    if len(raw) < min_len or len(raw) > max_len:
        print(f'Error: {msg_type} message has unexpected length {len(raw)}!')

class IridiumSBD():
    """Parses an Iridium SBD messge.

    attrs:
        header: A dictionary with the section header of an ISBD message.
    """
    def __init__(self, msg=None, key=None):
        """Initialize an IridiumSBD object.

        Args:
            msg (byte): A binary ISBD message (optional). If given, runs
                load(msg).
        """
        if msg is None:
            return

        self.load(msg, key)

    def __str__(self):
        return str(self.attrs)

    def load(self, raw, key):
        """Parse an Iridium SBD binary message."""
        self.attrs = collections.OrderedDict()
        self.attrs['(hex)'] = _hexlify(raw)

        self.attrs['message-type-(hex)'] = _hexlify(raw[0])
        if raw[0] not in _sbd_mo_msg_types:
            print(f'Error: Unexpected message type 0x{raw[0]:x}!')
            return
        msg_type =  _sbd_mo_msg_types[raw[0]]
        self.attrs['message-type'] = msg_type
        if msg_type in _sbd_mo_encrypted_msg_types:
            _check_msg_length(msg_type, raw, 10, 66)

        match msg_type:
            case 'unencrypted-position' | 'encrypted-position':
                _check_msg_length(msg_type, raw, 10, 18)
                self._parse_position_msg(msg_type, raw[1:], key)
            case 'encrypted-tlv-data':
                _check_msg_length(msg_type, raw, 12, 66)
                self._parse_tlv_data_msg(raw[1:])
            case 'unencrypted-tlv-data':
                _check_msg_length(msg_type, raw, 7, 66)
                self._parse_tlv_data_msg(raw[1:])
            case 'unencrypted-chained-position' | 'encrypted-chained-position':
                _check_msg_length(msg_type, raw, 8, 66)
                self._parse_position_msg(msg_type, raw[1:], key)
            case 'unencrypted-engineering' | 'encrypted-engineering':
                _check_msg_length(msg_type, raw, 33, 33)
                self._parse_eng_msg(msg_type, raw[1:], key)

    def _parse_position_msg(self, msg_type, raw, key):
        header_attrs = collections.OrderedDict()
        self.attrs['position-message-header'] = header_attrs
        msg_subtype = _parse_position_msg_header(raw[0], header_attrs)
        if msg_subtype is None:
            return

        match msg_subtype:
            case 'user-position':
                _check_position_msg_length(msg_type, msg_subtype, 17, raw)
            case _:
                _check_position_msg_length(msg_type, msg_subtype, 9, raw)

        payload_attrs = collections.OrderedDict()
        self.attrs['payload'] = payload_attrs
        parseable_payload = _decrypt_payload(msg_type, raw[1:], key, payload_attrs)
        if parseable_payload is None:
            return

        payload_attrs['(hex)'] = _hexlify(parseable_payload)
        _parse_position_msg_payload(msg_type, msg_subtype, parseable_payload, payload_attrs)

    def _parse_tlv_data_msg(self, raw):
        tlv_attrs = collections.OrderedDict()
        self.attrs['tlv'] = tlv_attrs

        tlv_attrs['(hex)'] = _hexlify(raw)
        (header, length, value) = _parse_tlv(raw[:len(raw)-3])
        tlv_attrs['type-(hex)'] = _hexlify(header)
        header_type = None
        if header not in _tlv_header_types:
            print(f'Error: unexpected header type 0x{header:x}!')
        else:
            header_type = _tlv_header_types[header]
            tlv_attrs['type'] = header_type
        tlv_attrs['length'] = length
        if length != len(value):
            print(f'Error: inconsistent TLV lengths {length} and {len(value)}!')

        tlv_attrs['value-(hex)'] = _hexlify(value)
        match header_type:
            case 'pad-tlv':
                # We just ignore any TLV padding, since it comes after the actual TLV message
                pass
            case 'config-updated':
                _parse_config_updated_tlv(length, value, tlv_attrs)
            case 'user-data':
                # We don't try to parse any user data
                pass
            case 'nak':
                _parse_nak_tlv(length, value, tlv_attrs)
            case _:
                print(f'Error: unknown TLV header type 0x{header:x}!')

        self.attrs['crc'] = f'0x{_hexlify(raw[len(raw)-3:])}'
        # TODO: check CRC

    def _parse_eng_msg(self, msg_type, raw, key):
        header_attrs = collections.OrderedDict()
        self.attrs['engineering-message-header'] = header_attrs

        payload_attrs = collections.OrderedDict()
        self.attrs['payload'] = payload_attrs
        parseable_payload = _decrypt_payload(msg_type, raw, key, payload_attrs)
        if parseable_payload is None:
            return

        payload_attrs['(hex)'] = _hexlify(parseable_payload)
        _parse_eng_msg_payload(parseable_payload, payload_attrs)


def print_attrs(attrs, indent='', verbose=False):
    """Print a nested dict of attributes in quasi-YAML-ish syntax."""
    for key, value in attrs.items():
        if '(' in key and not verbose:
            continue

        print(indent, end='')
        print(f'- {key}:', end='')
        if isinstance(value, collections.OrderedDict):
            print()
            print_attrs(value, indent=indent + '  ', verbose=verbose)
            continue
        print(f' {value}')


def dump(raw, key, verbose=False):
    """Parse and display SBD message as structured data."""
    msg = IridiumSBD(raw, key)
    print_attrs(msg.attrs, verbose=verbose)
