import redis

from balance_bridge.errors import KeystoreWriteError, KeystoreFetchError, KeystoreTokenExpiredError, FirebaseError


class RedisKeystore(object):

  def __init__(self, host='localhost', port=6379, db=0,
               charset='utf-8', decode_responses=True):
    self.redis_keystore = redis.StrictRedis(host=host, port=port,
                                            db=db, charset=charset,
                                            decode_responses=decode_responses)


  def connection_key(self, token):
    return "conn:{}".format(token)


  def transaction_key(self, transaction_uuid, device_uuid):
    return "txn:{}:{}".format(transaction_uuid, device_uuid)


  def write(self, key, value='', expiration_in_seconds=120, write_only_if_exists=False):
    success = self.redis_keystore.set(key, value, ex=expiration_in_seconds, xx=write_only_if_exists)
    return success


  def add_shared_connection(self, token):
    key = self.connection_key(token)
    success = self.write(key)
    if not success:
      raise KeystoreWriteError


  def update_connection_details(self, token, encrypted_payload):
    key = self.connection_key(token)
    success = self.write(key, encrypted_payload, write_only_if_exists=True)
    if not success:
      raise KeystoreTokenExpiredError


  def pop_connection_details(self, token):
    key = self.connection_key(token)
    details = self.redis_keystore.get(key)
    if details:
      self.redis_keystore.delete(key)
    return details


  def add_transaction(self, transaction_uuid, device_uuid, encrypted_payload):
    key = self.transaction_key(transaction_uuid, device_uuid)
    success = self.write(key, encrypted_payload)
    if not success:
      raise KeystoreWriteError


  def pop_transaction_details(self, transaction_uuid, device_uuid):
    key = self.transaction_key(transaction_uuid, device_uuid)
    details = self.redis_keystore.get(key)
    if not details:
      raise KeystoreFetchError
    else:
      self.redis_keystore.delete(key)
      return details


