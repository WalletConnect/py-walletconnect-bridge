import sys
import argparse
import uuid
import asyncio
import aiohttp
import uvloop
from aiohttp import web
import boto3

import wallet_connect.keystore
from wallet_connect.errors import KeystoreWriteError, KeystoreFetchError, WalletConnectPushError, KeystoreTokenExpiredError, KeystoreFcmTokenError

routes = web.RouteTableDef()

REDIS='org.wallet.connect.redis'
SESSION='org.wallet.connect.session'
LOCAL='local'
SERVICE='service'

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


@routes.get('/request-device-details')
async def request_device_details(request):
  try:
    session_token = str(uuid.uuid4())
    redis_conn = get_redis_master(request.app)
    await keystore.add_request_for_device_details(redis_conn, session_token)
    session_data = {"sessionToken": session_token}
    return web.json_response(session_data)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreWriteError:
    return web.json_response(error_message("Error writing to db"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/update-device-details')
async def update_device_details(request):
  request_json = await request.json()
  try:
    session_token = request_json['sessionToken']
    fcm_token = request_json['fcmToken']
    wallet_webhook = request_json['walletWebhook']
    encrypted_device_details = request_json['encryptedDeviceDetails']
    redis_conn = get_redis_master(request.app)
    device_uuid = str(uuid.uuid4())
    await keystore.add_device_fcm_data(redis_conn, device_uuid, wallet_webhook, fcm_token)
    await keystore.update_device_details(redis_conn, device_uuid, session_token, encrypted_device_details)
    device_uuid_data = {"deviceUuid": device_uuid}
    return web.json_response(device_uuid_data, status=202)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreTokenExpiredError:
    return web.json_response(error_message("Connection sharing token has expired"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/get-device-details')
async def get_device_details(request):
  try:
    request_json = await request.json()
    session_token = request_json['sessionToken']
    redis_conn = get_redis_master(request.app)
    device_details = await keystore.get_device_details(redis_conn, session_token)
    if device_details:
      return web.json_response(device_details)
    else: 
      return web.Response(status=204)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/add-transaction-details')
async def add_transaction_details(request):
  try:
    request_json = await request.json()
    transaction_uuid = str(uuid.uuid4())
    device_uuid = request_json['deviceUuid']
    encrypted_transaction_details = request_json['encryptedTransactionDetails']
    # TODO could be optional notification details
    notification_details = request_json['notificationDetails']
    redis_conn = get_redis_master(request.app)
    await keystore.add_transaction_details(redis_conn, transaction_uuid, device_uuid, encrypted_transaction_details)
    # Notify wallet webhook
    fcm_data = await keystore.get_device_fcm_data(redis_conn, device_uuid)
    session = request.app[SESSION]
    await send_webhook_request(session, fcm_data, device_uuid, transaction_uuid, notification_details)
    data_message = {"transactionUuid": transaction_uuid}
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


@routes.post('/get-transaction-details')
async def get_transaction_details(request):
  request_json = await request.json()
  try:
    transaction_uuid = request_json['transactionUuid']
    device_uuid = request_json['deviceUuid']
    redis_conn = get_redis_master(request.app)
    details = await keystore.get_transaction_details(redis_conn, transaction_uuid, device_uuid)
    json_response = {"encryptedTransactionDetails": details}
    return web.json_response(json_response)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreFetchError:
    return web.json_response(error_message("Error retrieving transaction details"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/update-transaction-status')
async def update_transaction_status(request):
  try:
    request_json = await request.json()
    transaction_uuid = request_json['transactionUuid']
    device_uuid = request_json['deviceUuid']
    encrypted_transaction_status = request_json['encryptedTransactionStatus']
    redis_conn = get_redis_master(request.app)
    await keystore.update_transaction_status(redis_conn, transaction_uuid, device_uuid, encrypted_transaction_status)
    return web.Response(status=201)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except:
      return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/get-transaction-status')
async def get_transaction_status(request):
  try:
    request_json = await request.json()
    transaction_uuid = request_json['transactionUuid']
    device_uuid = request_json['deviceUuid']
    redis_conn = get_redis_master(request.app)
    transaction_status = await keystore.get_transaction_status(redis_conn, transaction_uuid, device_uuid)
    if transaction_status:
      return web.json_response(transaction_status)
    else:
      return web.Response(status=204)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


async def send_webhook_request(session, fcm_data, device_uuid, transaction_uuid, notification_details):
  fcm_token = fcm_data['fcm_token']
  wallet_webhook = fcm_data['wallet_webhook']
  payload = {
    'deviceUuid': device_uuid,
    'transactionUuid': transaction_uuid,
    'fcmToken': fcm_token,
    'notificationDetails': notification_details
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
  asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
  web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
  main()
