import sys
import argparse
import uuid
import asyncio
import time
import aiohttp
from aiohttp import web
import boto3
try:
  import uvloop
except ModuleNotFoundError:
  pass

import walletconnect_bridge.keystore
from walletconnect_bridge.errors import KeystoreWriteError, KeystoreFetchError, WalletConnectPushError, KeystoreTokenExpiredError, KeystoreFcmTokenError

routes = web.RouteTableDef()

REDIS='org.wallet.connect.redis'
SESSION='org.wallet.connect.session'
LOCAL='local'
SERVICE='service'
SESSION_EXPIRATION = 24*60*60   # 24hrs
TX_DETAILS_EXPIRATION = 60*60   # 1hr

def error_message(message):
  return {"message": message}


def get_redis_master(app):
  if app[REDIS][LOCAL]:
    return app[REDIS][SERVICE]
  sentinel = app[REDIS][SERVICE]
  return sentinel.master_for('mymaster')


@routes.get('/hello')
async def hello(request):
  return web.Response(text="hello world, this is Wallet Connect")


@routes.post('/session/new')
async def new_session(request):
  try:
    session_id = str(uuid.uuid4())
    redis_conn = get_redis_master(request.app)
    await keystore.add_request_for_device_details(redis_conn, session_id, expiration_in_seconds=SESSION_EXPIRATION)
    now = time.time()
    expires = int((now + EXPIRATION) * 1000)
    session_data = {"sessionId": session_id, "expires": expires}
    return web.json_response(session_data)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreWriteError:
    return web.json_response(error_message("Error writing to db"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.put('/session/{sessionId}')
async def update_session(request):
  request_json = await request.json()
  try:
    session_id = request.match_info['sessionId']
    fcm_token = request_json['fcmToken']
    wallet_webhook = request_json['walletWebhook']
    data = request_json['data']
    redis_conn = get_redis_master(request.app)
    await keystore.add_device_fcm_data(redis_conn, session_id, wallet_webhook, fcm_token, expiration_in_seconds=SESSION_EXPIRATION)
    await keystore.update_device_details(redis_conn, session_id, data)
    return web.Response(status=200)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreTokenExpiredError:
    return web.json_response(error_message("Connection sharing token has expired"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.get('/session/{sessionId}')
async def get_session(request):
  try:
    session_id = request.match_info['sessionId']
    redis_conn = get_redis_master(request.app)
    device_details = await keystore.get_device_details(redis_conn, session_id)
    if device_details:
      session_data = {"data": device_details}
      return web.json_response(session_data)
    else:
      return web.Response(status=204)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/session/{sessionId}/transaction/new')
async def new_transaction(request):
  try:
    request_json = await request.json()
    transaction_id = str(uuid.uuid4())
    session_id = request.match_info['sessionId']
    data = request_json['data']
    # TODO could be optional notification details
    dapp_name = request_json['dappName']
    redis_conn = get_redis_master(request.app)
    await keystore.add_transaction_details(redis_conn, transaction_id, session_id, data, expiration_in_seconds=TX_DETAILS_EXPIRATION)
    # Notify wallet webhook
    fcm_data = await keystore.get_device_fcm_data(redis_conn, session_id)
    session = request.app[SESSION]
    await send_webhook_request(session, fcm_data, session_id, transaction_id, dapp_name)
    data_message = {"transactionId": transaction_id}
    return web.json_response(data_message, status=201)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreFcmTokenError:
    return web.json_response(error_message("Error finding FCM token for device"), status=500)
  except WalletConnectPushError:
    return web.json_response(error_message("Error sending message to wallet connect push endpoint"), status=500)
  except:
      return web.json_response(error_message("Error unknown"), status=500)


@routes.get('/session/{sessionId}/transaction/{transactionId}')
async def get_transaction(request):
  try:
    session_id = request.match_info['sessionId']
    transaction_id = request.match_info['transactionId']
    redis_conn = get_redis_master(request.app)
    details = await keystore.get_transaction_details(redis_conn, session_id, transaction_id)
    json_response = {"data": details}
    return web.json_response(json_response)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreFetchError:
    return web.json_response(error_message("Error retrieving transaction details"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/session/{sessionId}/transaction/{transactionId}/status/new')
async def new_transaction_status(request):
  try:
    request_json = await request.json()
    session_id = request.match_info['sessionId']
    transaction_id = request.match_info['transactionId']
    data = request_json['data']
    redis_conn = get_redis_master(request.app)
    await keystore.update_transaction_status(redis_conn, transaction_id, session_id, data)
    return web.Response(status=201)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except:
      return web.json_response(error_message("Error unknown"), status=500)


@routes.get('/session/{sessionId}/transaction/{transactionId}/status')
async def get_transaction_status(request):
  try:
    session_id = request.match_info['sessionId']
    transaction_id = request.match_info['transactionId']
    redis_conn = get_redis_master(request.app)
    transaction_status = await keystore.get_transaction_status(redis_conn, transaction_id, session_id)
    if transaction_status:
      json_response = {"data": transaction_status}
      return web.json_response(json_response)
    else:
      return web.Response(status=204)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


async def send_webhook_request(session, fcm_data, session_id, transaction_id, dapp_name):
  fcm_token = fcm_data['fcm_token']
  wallet_webhook = fcm_data['wallet_webhook']
  payload = {
    'sessionId': session_id,
    'transactionId': transaction_id,
    'fcmToken': fcm_token,
    'dappName': dapp_name
  }
  headers = {'Content-Type': 'application/json'}
  response = await session.post(wallet_webhook, json=payload, headers=headers)
  if response.status != 200:
    raise WalletConnectPushError


def get_kms_parameter(param_name):
  ssm = boto3.client('ssm', region_name='us-east-2')
  response = ssm.get_parameters(Names=[param_name], WithDecryption=True)
  return response['Parameters'][0]['Value']


async def initialize_client_session(app):
  app[SESSION] = aiohttp.ClientSession(loop=app.loop)


async def initialize_keystore(app):
  if app[REDIS][LOCAL]:
    app[REDIS][SERVICE] = await keystore.create_connection(event_loop=app.loop)
  else:
    sentinels = get_kms_parameter('wallet-connect-redis-sentinels')
    app[REDIS][SERVICE] = await keystore.create_sentinel_connection(event_loop=app.loop,
                                                           sentinels=sentinels.split(','))


async def close_keystore(app):
  app[REDIS][SERVICE].close()
  await app[REDIS][SERVICE].wait_closed()


async def close_client_session_connection(app):
  await app[SESSION].close()


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--redis-local', action='store_true')
  parser.add_argument('--no-uvloop', action='store_true')
  parser.add_argument('--host', type=str, default='localhost')
  parser.add_argument('--port', type=int, default=8080)
  args = parser.parse_args()

  app = web.Application()
  app[REDIS] = {LOCAL: args.redis_local}
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
