import aioredis

from balance_bridge.errors import KeystoreWriteError, KeystoreFetchError, KeystoreTokenExpiredError, FirebaseError, InvalidApiKey

async def create_connection(event_loop, host='localhost', port=6379, db=0):
  redis_uri = 'redis://{}:{}/{}'.format(host, port, db)
  return await aioredis.create_redis(address=redis_uri, db=db,
                                     encoding='utf-8', loop=event_loop)


async def create_sentinel_connection(event_loop, master, slave1, slave2):
  default_host = 26379
  sentinels = [(master, default_host), (slave1, default_host), (slave2, default_host)]
  sentinel = await aioredis.create_sentinel(sentinels, encoding='utf-8', loop=event_loop)
  return sentinel.master_for('mymaster')


async def add_shared_connection(conn, token):
  key = connection_key(token)
  success = await write(conn, key)
  if not success:
    raise KeystoreWriteError


async def update_connection_details(conn, token, encrypted_payload):
  key = connection_key(token)
  success = await write(conn, key, encrypted_payload, write_only_if_exists=True)
  if not success:
    raise KeystoreTokenExpiredError


async def pop_connection_details(conn, token):
  key = connection_key(token)
  details = await conn.get(key)
  if details:
    await conn.delete(key)
  return details


async def add_transaction(conn, transaction_uuid, device_uuid, encrypted_payload):
  key = transaction_key(transaction_uuid, device_uuid)
  success = await write(conn, key, encrypted_payload, expiration_in_seconds=300)
  if not success:
    raise KeystoreWriteError


async def pop_transaction_details(conn, transaction_uuid, device_uuid):
  key = transaction_key(transaction_uuid, device_uuid)
  details = await conn.get(key)
  if not details:
    raise KeystoreFetchError
  else:
    await conn.delete(key)
    return details


async def check_api_key(conn, api_key):
  if not api_key:
    raise InvalidApiKey
  key = api_redis_key(api_key)
  details = await conn.get(key)
  if not details:
    raise InvalidApiKey


def api_redis_key(api_key):
  return "apikey:{}".format(api_key)


def connection_key(token):
  return "conn:{}".format(token)


def transaction_key(transaction_uuid, device_uuid):
  return "txn:{}:{}".format(transaction_uuid, device_uuid)


async def write(conn, key, value='', expiration_in_seconds=120, write_only_if_exists=False):
  exist = 'SET_IF_EXIST' if write_only_if_exists else None
  success = await conn.set(key, value, expire=expiration_in_seconds, exist=exist)
  return success
