import sys
import argparse
import uuid
import asyncio
import aiohttp
import pkg_resources
from aiohttp import web
try:
  import uvloop
except ModuleNotFoundError:
  pass

import walletconnect_bridge.keystore
from walletconnect_bridge.time import now
from walletconnect_bridge.errors import KeystoreWriteError, KeystoreFetchError, WalletConnectPushError, KeystoreTokenExpiredError, KeystorePushTokenError

routes = web.RouteTableDef()

WC_VERSION = pkg_resources.require("walletconnect-bridge")[0].version
REDIS='org.wallet.connect.redis'
SESSION='org.wallet.connect.session'
SENTINEL='sentinel'
SENTINELS='sentinels'
HOST='host'
SERVICE='service'
SESSION_EXPIRATION = 24*60*60   # 24hrs
TX_DETAILS_EXPIRATION = 60*60   # 1hr

def error_message(message):
  return {'message': message}


def get_redis_master(app):
  if app[REDIS][SENTINEL]:
    sentinel = app[REDIS][SERVICE]
    return sentinel.master_for('mymaster')
  return app[REDIS][SERVICE]

@routes.get('/hello')
async def hello(request):
  message = 'Hello World, this is WalletConnect v{}'.format(WC_VERSION)
  return web.Response(text=message)

@routes.get('/info')
async def get_info(request):
  bridge_details = {'name': 'WalletConnect Bridge Server', 'repository': 'py-walletconnect-bridge', 'version': WC_VERSION}
  return web.json_response(bridge_details)

@routes.post('/session/new')
async def new_session(request):
  try:
    session_id = str(uuid.uuid4())
    redis_conn = get_redis_master(request.app)
    await keystore.add_request_for_session_details(redis_conn, session_id, expiration_in_seconds=SESSION_EXPIRATION)
    session_data = {'sessionId': session_id}
    return web.json_response(session_data)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except KeystoreWriteError:
    return web.json_response(error_message('Error writing to db'), status=500)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


@routes.put('/session/{sessionId}')
async def update_session(request):
  request_json = await request.json()
  try:
    session_id = request.match_info['sessionId']
    push_data = request_json['push']
    data = request_json['encryptionPayload']
    session_details = {'encryptionPayload': data}
    redis_conn = get_redis_master(request.app)
    await keystore.add_push_data(redis_conn, session_id, push_data, expiration_in_seconds=SESSION_EXPIRATION)
    expires = await keystore.update_session_details(redis_conn, session_id, session_details, expiration_in_seconds=SESSION_EXPIRATION)
    session_data = {'expires': expires}
    return web.json_response(session_data)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except KeystoreTokenExpiredError:
    return web.json_response(error_message('Connection sharing token has expired'), status=500)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


@routes.get('/session/{sessionId}')
async def get_session(request):
  try:
    session_id = request.match_info['sessionId']
    redis_conn = get_redis_master(request.app)
    (session_details, expires) = await keystore.get_session_details(redis_conn, session_id)
    if session_details:
      session_data = {'data': { 'encryptionPayload': session_details, 'expires': expires}}
      return web.json_response(session_data)
    else:
      return web.Response(status=204)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


@routes.delete('/session/{sessionId}')
async def remove_session(request):
  try:
    session_id = request.match_info['sessionId']
    redis_conn = get_redis_master(request.app)
    await keystore.remove_push_data(redis_conn, session_id)
    await keystore.remove_session_details(redis_conn, session_id)
    return web.Response(status=200)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


@routes.post('/session/{sessionId}/call/new')
async def new_call(request):
  try:
    request_json = await request.json()
    call_id = str(uuid.uuid4())
    session_id = request.match_info['sessionId']
    data = request_json['encryptionPayload']
    call_data = {'encryptionPayload': data}
    # TODO could be optional notification details
    dapp_name = request_json['dappName']
    redis_conn = get_redis_master(request.app)
    await keystore.add_call_details(redis_conn, call_id, session_id, call_data, expiration_in_seconds=TX_DETAILS_EXPIRATION)
    # Notify wallet push endpoint
    push_data = await keystore.get_push_data(redis_conn, session_id)
    session = request.app[SESSION]
    await send_push_request(session, push_data, session_id, call_id, dapp_name)
    data_message = {'callId': call_id}
    return web.json_response(data_message, status=201)
  except KeystorePushTokenError:
    return web.json_response(error_message('Push token for this session is no longer available'), status=500)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except KeystorePushTokenError:
    return web.json_response(error_message('Error finding Push token for session'), status=500)
  except WalletConnectPushError:
    return web.json_response(error_message('Error sending message to wallet connect push endpoint'), status=500)
  except:
      return web.json_response(error_message('Error unknown'), status=500)


@routes.get('/session/{sessionId}/call/{callId}')
async def get_call(request):
  try:
    session_id = request.match_info['sessionId']
    call_id = request.match_info['callId']
    redis_conn = get_redis_master(request.app)
    details = await keystore.get_call_details(redis_conn, session_id, call_id)
    json_response = {'data': details}
    return web.json_response(json_response)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except KeystoreFetchError:
    return web.json_response(error_message('Error retrieving call details'), status=500)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


@routes.get('/session/{sessionId}/calls')
async def get_all_calls(request):
  try:
    session_id = request.match_info['sessionId']
    redis_conn = get_redis_master(request.app)
    details = await keystore.get_all_calls(redis_conn, session_id)
    json_response = {'data': details}
    return web.json_response(json_response)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except KeystoreFetchError:
    return web.json_response(error_message('Error retrieving call details'), status=500)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


@routes.post('/call-status/{callId}/new')
async def new_call_status(request):
  try:
    request_json = await request.json()
    call_id = request.match_info['callId']
    data = request_json['encryptionPayload']
    call_status_data = {'encryptionPayload': data}
    redis_conn = get_redis_master(request.app)
    await keystore.update_call_status(redis_conn, call_id, call_status_data)
    return web.Response(status=201)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except TypeError:
    return web.json_response(error_message('Incorrect JSON content type'), status=400)
  except:
      return web.json_response(error_message('Error unknown'), status=500)


@routes.get('/call-status/{callId}')
async def get_call_status(request):
  try:
    call_id = request.match_info['callId']
    redis_conn = get_redis_master(request.app)
    call_status = await keystore.get_call_status(redis_conn, call_id)
    if call_status:
      json_response = {'data': call_status}
      return web.json_response(json_response)
    else:
      return web.Response(status=204)
  except KeyError:
    return web.json_response(error_message('Incorrect input parameters'), status=400)
  except:
    return web.json_response(error_message('Error unknown'), status=500)


async def send_push_request(session, push_data, session_id, call_id, dapp_name):
  push_type = push_data['type']
  push_token = push_data['token']
  push_endpoint = push_data['endpoint']
  payload = {
    'sessionId': session_id,
    'callId': call_id,
    'pushType': push_type,
    'pushToken': push_token,
    'dappName': dapp_name
  }
  headers = {'Content-Type': 'application/json'}
  response = await session.post(push_endpoint, json=payload, headers=headers)
  if response.status != 200:
    raise WalletConnectPushError


async def initialize_client_session(app):
  app[SESSION] = aiohttp.ClientSession(loop=app.loop)


async def initialize_keystore(app):
  if app[REDIS][SENTINEL]:
    sentinels = app[REDIS][SENTINELS].split(',')
    app[REDIS][SERVICE] = await keystore.create_sentinel_connection(event_loop=app.loop,
                                                                    sentinels=sentinels)
  else:
    app[REDIS][SERVICE] = await keystore.create_connection(event_loop=app.loop,
                                                           host=app[REDIS][HOST])


async def close_keystore(app):
  app[REDIS][SERVICE].close()
  await app[REDIS][SERVICE].wait_closed()


async def close_client_session_connection(app):
  await app[SESSION].close()


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--redis-use-sentinel', action='store_true')
  parser.add_argument('--sentinels', type=str)
  parser.add_argument('--redis-host', type=str, default='localhost')
  parser.add_argument('--no-uvloop', action='store_true')
  parser.add_argument('--host', type=str, default='localhost')
  parser.add_argument('--port', type=int, default=8080)
  args = parser.parse_args()

  app = web.Application()
  app[REDIS] = {
    SENTINEL: args.redis_use_sentinel,
    SENTINELS: args.sentinels,
    HOST: args.redis_host
  }
  app.on_startup.append(initialize_client_session)
  app.on_startup.append(initialize_keystore)
  app.on_cleanup.append(close_keystore)
  app.on_cleanup.append(close_client_session_connection)
  app.router.add_routes(routes)
  if not args.no_uvloop:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
  web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
  main()
