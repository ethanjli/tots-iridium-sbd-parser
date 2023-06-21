#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Command line utilities for sbd package"""

import logging
import logging.handlers

import click

from .sbd import dump


@click.group()
@click.option(
        '--loglevel',
        type=click.Choice(['debug', 'info', 'warn', 'error']),
        default='info')
@click.option('--logfile', default=None)
def main(loglevel, logfile):
    """ Utilities for Iridium DirectIP communication
    """
    # create logger with 'directip'
    logger = logging.getLogger('DirectIP')
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG)

    if logfile is not None:
        # create file handler which logs even debug messages
        file_handler = logging.handlers.RotatingFileHandler(
            logfile, maxBytes=(1024**2), backupCount=10)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(getattr(logging, loglevel.upper()))
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.debug('Running DirectIP command line.')


@main.command(name='dump')
@click.argument('file', type=click.File('rb'))
@click.option('--imei', is_flag=True, help='Show IMEI only')
def isbddump(file, imei):
    """ Temporary solution to dump an ISBD message
    """
    return dump(file, imei)


if __name__ == '__main__':
    main()
