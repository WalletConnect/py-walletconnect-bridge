import aioredis
import json

from wallet_connect.errors import KeystoreWriteError, KeystoreFetchError, KeystoreTokenExpiredError, FirebaseError, InvalidApiKey, KeystoreFcmTokenError

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


async def add_request_for_device_details(conn, session_token):
  key = session_key(session_token)
  success = await write(conn, key, '', expiration_in_seconds=5*60)
  if not success:
    raise KeystoreWriteError('Error adding request for details')


async def update_device_details(conn, device_uuid, session_token, encrypted_payload):
  key = session_key(session_token)
  data = {'deviceUuid': device_uuid, 'encryptedPayload': encrypted_payload}
  device_data = json.dumps(data)
  success = await write(conn, key, device_data, write_only_if_exists=True)
  if not success:
    raise KeystoreTokenExpiredError


async def add_device_fcm_token(conn, device_uuid, fcm_token):
  key = device_uuid_key(device_uuid)
  success = await write(conn, key, fcm_token, expiration_in_seconds=30*60)
  if not success:
    raise KeystoreWriteError("Could not write device FCM token")
  

async def get_device_fcm_token(conn, device_uuid):
  device_key = device_uuid_key(device_uuid)
  fcm_token = await conn.get(device_key)
  if not fcm_token:
    raise KeystoreFcmTokenError
  return fcm_token


async def get_device_details(conn, session_token):
  key = session_key(session_token)
  details = await conn.get(key)
  if details:
    await conn.delete(key)
    return json.loads(details)
  return None


async def add_transaction_details(conn, transaction_uuid, device_uuid, encrypted_payload):
  key = transaction_key(transaction_uuid, device_uuid)
  success = await write(conn, key, encrypted_payload, expiration_in_seconds=300)
  if not success:
    raise KeystoreWriteError("Error adding transaction details")


async def get_transaction_details(conn, transaction_uuid, device_uuid):
  key = transaction_key(transaction_uuid, device_uuid)
  details = await conn.get(key)
  if not details:
    raise KeystoreFetchError("Error getting transaction details")
  else:
    await conn.delete(key)
    return details


async def add_transaction_hash(conn, transaction_uuid, device_uuid, transaction_hash):
  key = transaction_hash_key(transaction_uuid, device_uuid)
  success = await write(conn, key, transaction_hash)
  if not success:
    raise KeystoreWriteError("Error writing transaction hash")


async def get_transaction_hash(conn, transaction_uuid, device_uuid):
  key = transaction_hash_key(transaction_uuid, device_uuid)
  transaction_hash = await conn.get(key)
  if transaction_hash:
    await conn.delete(key)
  return transaction_hash


def api_redis_key(api_key):
  return "apikey:{}".format(api_key)


def session_key(session_token):
  return "session:{}".format(session_token)


def device_uuid_key(device_uuid):
  return "device:{}".format(device_uuid)


def transaction_key(transaction_uuid, device_uuid):
  return "txn:{}:{}".format(transaction_uuid, device_uuid)


def transaction_hash_key(transaction_uuid, device_uuid):
  return "txnhash:{}:{}".format(transaction_uuid, device_uuid)


async def write(conn, key, value='', expiration_in_seconds=120, write_only_if_exists=False):
  exist = 'SET_IF_EXIST' if write_only_if_exists else None
  success = await conn.set(key, value, expire=expiration_in_seconds, exist=exist)
  return success
