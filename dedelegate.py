#! /usr/bin/env python3
# coding=utf-8
import time
import configargparse
import os
import json
import logging
import statistics
import sys

from redeemer import Dedelegator

def gather_stats(results):
  for (account, dedelegation_amount) in results:
    pass   

parser = configargparse.ArgumentParser('redeemer', formatter_class=configargparse.ArgumentDefaultsRawHelpFormatter)
parser.add_argument('--account', type=str, help='Account to perform dedelegations for')
parser.add_argument('--wif', type=configargparse.FileType('r'), help='An active WIF for account. The flag expects a path to a file. The environment variable REDEEMER_WIF will be checked for a literal WIF also.')
parser.add_argument('--log_level', type=str, default='INFO')
parser.add_argument('--dry_run', type=bool, default=True, help='Set this to false to actually broadcast transactions')
parser.add_argument('--interval', type=int, default=60, help='Time in seconds to wait between polling for new delegations')

args = parser.parse_args()

logger = logging.getLogger("redeemer")
logging.basicConfig(level=logging.getLevelName(args.log_level))

wif = None
if args.wif:
    logger.info('Using wif from file %s' % args.wif)
    wif = args.wif.read().strip()
elif os.environ.get('REDEEMER_WIF') is not None:
    logger.info('Using wif from environment variable REDEEMER_WIF')
    wif = os.environ.get('REDEEMER_WIF')
else:
    logger.warn('You have not specified a wif; signing transactions is not possible!')

if args.dry_run:
  logger.warn("dry run mode; no transactions will be broadcast")

dedelegator = Dedelegator(logger=logger)

while True:
  last_idx = -1
  while True:
    try:
      logger.info("at index %d", last_idx)
      results, last_idx = dedelegator.dedelegate(args.account, last_idx=last_idx, dry_run=args.dry_run)
      gather_stats(results)
      if len(results) == 0:
        break
    except Exception as e:
      logger.exception("failed to dedelegate")
      break
  logger.info("Waiting %d seconds until the next run", args.interval)
  time.sleep(args.interval)

