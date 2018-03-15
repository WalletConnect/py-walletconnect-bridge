import redis

redis_keystore = redis.StrictRedis(host='localhost', port=6379, db=0, charset='utf-8', decode_responses=True)

class KeystoreWriteError(Exception):
  pass


class KeystoreFetchError(Exception):
  pass


def connection_key(token):
  return "conn:{}".format(token)


def transaction_key(transaction_uuid, device_uuid):
  return "txn:{}:{}".format(transaction_uuid, device_uuid)


def add_shared_connection(token):
  key = connection_key(token)
  success = redis_keystore.set(key, '')
  if not success:
    raise KeystoreWriteError()


def update_connection_details(token, encrypted_payload):
  key = connection_key(token)
  success = redis_keystore.set(key, encrypted_payload)
  if not success:
    raise KeystoreWriteError()


def pop_connection_details(token):
  key = connection_key(token)
  details = redis_keystore.get(key)
  if details:
    print(details)
    redis_keystore.delete(key)
  return details


def add_transaction(transaction_uuid, device_uuid, encrypted_payload):
  key = transaction_key(transaction_uuid, device_uuid)
  success = redis_keystore.set(key, encrypted_payload)
  if not success:
    raise KeystoreWriteError()


def pop_transaction_details(transaction_uuid, device_uuid):
  key = transaction_key(transaction_uuid, device_uuid)
  details = redis_keystore.get(key)
  if not details:
    raise KeystoreFetchError
  else:
    redis_keystore.delete(key)
    return details


