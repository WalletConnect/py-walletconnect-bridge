import aioredis
import json

from walletconnect_bridge.errors import KeystoreWriteError, KeystoreFetchError, KeystoreTokenExpiredError, KeystoreFcmTokenError

async def create_connection(event_loop, host='localhost', port=6379, db=0):
  redis_uri = 'redis://{}:{}/{}'.format(host, port, db)
  return await aioredis.create_redis(address=redis_uri, db=db,
                                     encoding='utf-8', loop=event_loop)


async def create_sentinel_connection(event_loop, sentinels):
  default_port = 26379
  sentinel_ports = [(x, default_port) for x in sentinels]
  sentinel = await aioredis.create_sentinel(sentinel_ports,
                                            encoding='utf-8',
                                            loop=event_loop)
  return sentinel


async def add_request_for_device_details(conn, session_id):
  key = session_key(session_id)
  success = await write(conn, key, '', expiration_in_seconds=24*60*60)
  if not success:
    raise KeystoreWriteError('Error adding request for details')


async def update_device_details(conn, session_id, data):
  key = session_key(session_id)
  device_data = json.dumps(data)
  success = await write(conn, key, device_data, write_only_if_exists=True)
  if not success:
    raise KeystoreTokenExpiredError


async def get_device_details(conn, session_id):
  key = session_key(session_id)
  details = await conn.get(key)
  if details:
    await conn.delete(key)
    return json.loads(details)
  else:
    return None


async def add_device_fcm_data(conn, session_id, wallet_webhook, fcm_token):
  # TODO what if we want wallet_webhook to be null?
  key = fcm_device_key(session_id)
  data = {'fcm_token': fcm_token, 'wallet_webhook': wallet_webhook}
  fcm_data = json.dumps(data)
  success = await write(conn, key, fcm_data, expiration_in_seconds=24*60*60)
  if not success:
    raise KeystoreWriteError("Could not write device FCM data")


async def get_device_fcm_data(conn, session_id):
  device_key = fcm_device_key(session_id)
  data = await conn.get(device_key)
  if not data:
    raise KeystoreFcmTokenError
  return json.loads(data)


async def add_transaction_details(conn, transaction_id, session_id, data):
  key = transaction_key(transaction_id, session_id)
  # TODO how long should this be here for?
  txn_data = json.dumps(data)
  success = await write(conn, key, txn_data, expiration_in_seconds=60*60)
  if not success:
    raise KeystoreWriteError("Error adding transaction details")


async def get_transaction_details(conn, session_id, transaction_id):
  key = transaction_key(transaction_id, session_id)
  details = await conn.get(key)
  if not details:
    raise KeystoreFetchError("Error getting transaction details")
  else:
    await conn.delete(key)
    return json.loads(details)


async def update_transaction_status(conn, transaction_id, session_id, data):
  key = transaction_hash_key(transaction_id, session_id)
  transaction_status = json.dumps(data)
  success = await write(conn, key, transaction_status)
  if not success:
    raise KeystoreWriteError("Error adding transaction status")


async def get_transaction_status(conn, transaction_id, session_id):
  key = transaction_hash_key(transaction_id, session_id)
  encrypted_transaction_status = await conn.get(key)
  if encrypted_transaction_status:
    await conn.delete(key)
    return json.loads(encrypted_transaction_status)
  else:
    return None


def session_key(session_id):
  return "session:{}".format(session_id)


def fcm_device_key(session_id):
  return "fcmdevice:{}".format(session_id)


def transaction_key(transaction_id, session_id):
  return "txn:{}:{}".format(transaction_id, session_id)


def transaction_hash_key(transaction_id, session_id):
  return "txnhash:{}:{}".format(transaction_id, session_id)


async def write(conn, key, value='', expiration_in_seconds=60*10, write_only_if_exists=False):
  exist = 'SET_IF_EXIST' if write_only_if_exists else None
  success = await conn.set(key, value, expire=expiration_in_seconds, exist=exist)
  return success
