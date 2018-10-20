import aioredis
import json

from walletconnect_bridge.time import get_expiration_time
from walletconnect_bridge.errors import KeystoreWriteError, KeystoreFetchError, KeystoreTokenExpiredError, KeystorePushTokenError

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


async def add_request_for_session_data(conn, session_id, expiration_in_seconds):
  key = session_key(session_id)
  success = await write(conn, key, '', expiration_in_seconds)
  if not success:
    raise KeystoreWriteError('Error adding request for data')



async def update_session_data(conn, session_id, session_data, expiration_in_seconds):
  key = session_key(session_id)
  data = json.dumps(session_data)
  success = await write(conn, key, data, expiration_in_seconds, write_only_if_exists=True)
  expires = get_expiration_time(ttl_in_seconds=expiration_in_seconds)
  if not success:
    raise KeystoreTokenExpiredError
  return expires



async def get_session_data(conn, session_id):
  key = session_key(session_id)
  data = await conn.get(key)
  if data:
    ttl_in_seconds = await conn.ttl(key)
    expires = get_expiration_time(ttl_in_seconds)
    session_data = json.loads(data)
    session_data['expires'] = expires
    return session_data
  else:
    return None


async def remove_session_data(conn, session_id):
  key = session_key(session_id)
  await conn.delete(key)


async def add_push_data(conn, session_id, push_data, expiration_in_seconds):
  key = push_session_key(session_id)
  data = json.dumps(push_data)
  success = await write(conn, key, data, expiration_in_seconds)
  expires = get_expiration_time(ttl_in_seconds=expiration_in_seconds)
  if not success:
    raise KeystoreWriteError('Could not write session Push data')
  return expires


async def get_push_data(conn, session_id):
  session_key = push_session_key(session_id)
  data = await conn.get(session_key)
  if not data:
    return None
  return json.loads(data)


async def remove_push_data(conn, session_id):
  session_key = push_session_key(session_id)
  await conn.delete(session_key)


async def add_call_data(conn, session_id, call_id, call_data, expiration_in_seconds):
  key = call_key(session_id, call_id)
  data = json.dumps(call_data)
  success = await write(conn, key, data, expiration_in_seconds)
  if not success:
    raise KeystoreWriteError('Error adding call data')


async def get_call_data(conn, session_id, call_id):
  key = call_key(session_id, call_id)
  data = await conn.get(key)
  if not data:
    raise KeystoreFetchError('Error getting call data')
  else:
    await conn.delete(key)
    return json.loads(data)


async def get_all_calls(conn, session_id):
  key = call_key(session_id, '*')
  all_keys = []
  cur = b'0'  # set initial cursor to 0
  while cur:
    cur, keys = await conn.scan(cur, match=key)
    all_keys.extend(keys);
  if not all_keys:
    return {}
  data = await conn.mget(*all_keys)
  call_ids = map(lambda x: x.split(':')[2], all_keys)
  zipped_results = dict(zip(call_ids, data))
  filtered_results = {k: json.loads(v) for k, v in zipped_results.items() if v}
  await conn.delete(*all_keys)
  return filtered_results


async def update_call_status(conn, call_id, call_status):
  key = call_status_key(call_id)
  data = json.dumps(call_status)
  success = await write(conn, key, data)
  if not success:
    raise KeystoreWriteError('Error adding call status')


async def get_call_status(conn, call_id):
  key = call_status_key(call_id)
  data = await conn.get(key)
  if data:
    await conn.delete(key)
    return json.loads(data)
  else:
    return None


def session_key(session_id):
  return 'session:{}'.format(session_id)


def push_session_key(session_id):
  return 'pushsession:{}'.format(session_id)


def call_key(session_id, call_id):
  return 'call:{}:{}'.format(session_id, call_id)


def call_status_key(call_id):
  return 'callstatus:{}'.format(call_id)


async def write(conn, key, value='', expiration_in_seconds=60*60, write_only_if_exists=False):
  exist = 'SET_IF_EXIST' if write_only_if_exists else None
  success = await conn.set(key, value, expire=expiration_in_seconds, exist=exist)
  return success
