import logging

from steem import Steem
from steem.steemd import Steemd
from steem.instance import set_shared_steemd_instance
from steem.converter import Converter
from steembase import operations
from steem.amount import Amount
from steem.transactionbuilder import TransactionBuilder

class Delegator(object):

  def __init__(self, steem=None, limit=1000, logger=logging.NullHandler):
      if steem is None:
        dry_run = True
        self.steem = Steem(nodes=['https://api.steemit.com'])
      else:
        self.steem = steem
      self.limit = limit
      self.logger = logger
      self.converter = Converter(steemd_instance=self.steem)
      INCLUSIVE_LOWER_BALANCE_LIMIT_SP = 15
      self.INCLUSIVE_LOWER_BALANCE_LIMIT_VESTS = Amount('%s VESTS' % int(self.converter.sp_to_vests(INCLUSIVE_LOWER_BALANCE_LIMIT_SP)))

  def get_delegated_accounts(self, account, last_idx=0):
      results = self.steem.get_vesting_delegations(account, last_idx, self.limit)
      account_names = [result['delegatee'] for result in results] 
      accounts = self.steem.get_accounts(account_names)
      for i, account in enumerate(accounts):
        account['vesting_shares_from_delegator'] = results[i]['vesting_shares']
        
      return (accounts, account_names[len(account_names)-1])

  def vests_to_delegate(self, acct):
      name = acct['name']
      acct_vests = Amount(acct['vesting_shares'])
      delegated_vests = Amount(acct['received_vesting_shares'])
      beginning_balance = acct_vests + delegated_vests
      v = self.INCLUSIVE_LOWER_BALANCE_LIMIT_VESTS - beginning_balance

      # cant undelegate amount greater than current delegation
      if v < 0 and abs(float(v)) > delegated_vests:
          v =  -1.0 * float(delegated_vests)
          v = Amount('%s VESTS' % v)

      return v

  def get_delegation_op(self, delegator_account_name, account):
      return operations.DelegateVestingShares(
          delegator=delegator_account_name,
          vesting_shares=str(self.vests_to_delegate(account)),
          delegatee=account['name']
      )    
 
  def delegate(self, delegator_account_name, last_idx, expiration=60, dry_run=True, wifs=[]):
    accounts, last_idx = self.get_delegated_accounts(delegator_account_name, last_idx=last_idx)
    if len(accounts) == 0:
      return ([], last_idx)
    delegation_ops = [ self.get_delegation_op(delegator_account_name, account) for account in accounts ]
    tx = TransactionBuilder(steemd_instance=self.steem, expiration=expiration)
    tx.appendOps(delegation_ops)
    [ tx.appendWif(wif) for wif in wifs ]
    if len(wifs) is not 0:
      tx.sign()
    if not dry_run:
      result = tx.broadcast()
      self.logger.info('transaction broadcast. result: %s', result)
    return (
      [(account, self.vests_to_delegate(account)) for account in accounts ],
      last_idx
    )

