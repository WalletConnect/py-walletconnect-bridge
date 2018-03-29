import sys
import argparse
import uuid
import asyncio
import aiohttp
import uvloop
from aiohttp import web
import boto3

import wallet_connect.keystore
from wallet_connect.errors import KeystoreWriteError, KeystoreFetchError, FirebaseError, KeystoreTokenExpiredError, InvalidApiKey, KeystoreFcmTokenError

routes = web.RouteTableDef()

API='io.wallet.connect.api_gateway'
REDIS='io.wallet.connect.redis'
SESSION='io.wallet.connect.session'
KEY='key'
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
  return web.Response(text="hello world")


async def check_authorization(request):
  if 'Authorization' not in request.headers:
    raise InvalidApiKey
  api_key = request.headers['Authorization']
  if request.app[API][KEY] != api_key:
    raise InvalidApiKey


@routes.get('/request-device-details')
async def request_device_details(request):
  try:
    await check_authorization(request)
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
  except InvalidApiKey:
      return web.json_response(error_message("Unauthorized"), status=401)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/update-device-details')
async def update_device_details(request):
  request_json = await request.json()
  try:
    session_token = request_json['sessionToken']
    fcm_key = request_json['fcmKey']
    wallet_webhook = request_json['walletWebhook']
    encrypted_payload = request_json['encryptedPayload']
    redis_conn = get_redis_master(request.app)
    device_uuid = str(uuid.uuid4())
    await keystore.add_device_fcm_data(redis_conn, device_uuid, wallet_webhook, fcm_key)
    await keystore.update_device_details(redis_conn, device_uuid, session_token, encrypted_payload)
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
    await check_authorization(request)
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
  except InvalidApiKey:
      return web.json_response(error_message("Unauthorized"), status=401)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/add-transaction-details')
async def add_transaction_details(request):
  try:
    await check_authorization(request)
    request_json = await request.json()
    transaction_uuid = str(uuid.uuid4())
    device_uuid = request_json['deviceUuid']
    encrypted_payload = request_json['encryptedPayload']
    # TODO could be optional notification details
    notification_title = request_json['notificationTitle']
    notification_body = request_json['notificationBody']
    redis_conn = get_redis_master(request.app)
    await keystore.add_transaction_details(redis_conn, transaction_uuid, device_uuid, encrypted_payload)

    # Notify wallet webhook
    fcm_data = await keystore.get_device_fcm_data(redis_conn, device_uuid)
    session = request.app[SESSION]
    await send_webhook_request(session, fcm_data, transaction_uuid, notification_title, notification_body)
    data_message = {"transactionUuid": transaction_uuid}
    return web.json_response(data_message, status=201)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreFcmTokenError:
    return web.json_response(error_message("Error finding FCM token for device"), status=500)
  except FirebaseError:
    return web.json_response(error_message("Error pushing notifications through Firebase"), status=500)
  except InvalidApiKey:
      return web.json_response(error_message("Unauthorized"), status=401)
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
    json_response = {"encryptedPayload": details}
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
    transaction_status = request_json['transactionStatus']
    transaction_hash = request_json['transactionHash'] if ('transactionHash' in request_json) else None
    redis_conn = get_redis_master(request.app)
    await keystore.update_transaction_status(redis_conn, transaction_uuid, device_uuid,
                                             transaction_status, transaction_hash)
    return web.Response(status=201)
  except KeyError:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except FirebaseError:
    return web.json_response(error_message("Error pushing notifications through Firebase"), status=500)
  except InvalidApiKey:
      return web.json_response(error_message("Unauthorized"), status=401)
  except:
      return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/get-transaction-status')
async def get_transaction_status(request):
  try:
    await check_authorization(request)
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
  except InvalidApiKey:
      return web.json_response(error_message("Unauthorized"), status=401)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


async def send_webhook_request(session, fcm_data, transaction_uuid, notification_title,
                               notification_body):
  fcm_key = fcm_data['fcm_key']
  wallet_webhook = fcm_data['wallet_webhook']
  payload = {
    'transactionUuid': transaction_uuid,
    'fcmKey': fcm_key,
    'notificationTitle': notification_title,
    'notificationBody': notification_body
  }
  headers = {'Content-Type': 'application/json'}
  response = await session.post(wallet_webhook, json=payload, headers=headers)
  if response.status != 200:
    raise FirebaseError("Wallet webhook error")


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


async def initialize_api_gateway(app):
  if app[API][LOCAL]:
    app[API][KEY] = 'dummy_api_key'
  else:
    app[API][KEY] = get_kms_parameter('wallet-connect-manager-api-key')


async def close_keystore(app):
  app[REDIS][SERVICE].close()
  await app[REDIS][SERVICE].wait_closed()


async def close_client_session_connection(app):
  await app[SESSION].close()


def main(): 
  parser = argparse.ArgumentParser()
  parser.add_argument('--redis-local', action='store_true')
  parser.add_argument('--api-local', action='store_true')
  parser.add_argument('--host', type=str, default='localhost')
  parser.add_argument('--port', type=int, default=8080)
  args = parser.parse_args()

  app = web.Application()
  app[API] = {LOCAL: args.api_local}
  app[REDIS] = {LOCAL: args.redis_local}
  app.on_startup.append(initialize_client_session)
  app.on_startup.append(initialize_keystore)
  app.on_startup.append(initialize_api_gateway)
  app.on_cleanup.append(close_keystore)
  app.on_cleanup.append(close_client_session_connection)
  app.router.add_routes(routes)
  asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
  web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
  main()
