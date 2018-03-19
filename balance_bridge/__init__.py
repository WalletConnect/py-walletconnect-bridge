import sys
import argparse

import asyncio
import aiohttp
import uvloop
from aiohttp import web
import boto3

import balance_bridge.keystore
from balance_bridge.push_notifications import PushNotificationsService
from balance_bridge.errors import KeystoreWriteError, KeystoreFetchError, FirebaseError, KeystoreTokenExpiredError

routes = web.RouteTableDef()

REDIS='io.balance.bridge.redis'
PUSH='io.balance.bridge.push_notifications'
LOCAL='local'
SERVICE='service'

def error_message(message):
  return {"message": message}


@routes.get('/hello')
async def hello(request):
  return web.Response(text="hello world")


@routes.put('/create_shared_connection')
async def create_shared_connection(request):
  request_json = await request.json()
  try:
    token = request_json['token']
    redis_conn = request.app[REDIS][SERVICE]
    await keystore.add_shared_connection(redis_conn, token)
  except KeyError as ke:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError as te:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreWriteError as kwe:
    return web.json_response(error_message("Error writing to db"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)
  return web.Response(status=201)


@routes.post('/update_connection_details')
async def update_connection_details(request):
  request_json = await request.json()
  try:
    token = request_json['token']
    encrypted_payload = request_json['encrypted_payload']
    redis_conn = request.app[REDIS][SERVICE]
    await keystore.update_connection_details(redis_conn, token, encrypted_payload)
  except KeyError as ke:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError as te:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreTokenExpiredError as ktee:
    return web.json_response(error_message("Connection sharing token has expired"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)
  return web.Response(status=202)


@routes.post('/pop_connection_details')
async def pop_connection_details(request):
  request_json = await request.json()
  try:
    token = request_json['token']
    redis_conn = request.app[REDIS][SERVICE]
    connection_details = await keystore.pop_connection_details(redis_conn, token)
    if connection_details:
      json_response = {"encrypted_payload": connection_details}
      return web.json_response(json_response)
    else: 
      return web.Response(status=204)
  except KeyError as ke:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError as te:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


@routes.put('/initiate_transaction')
async def initiate_transaction(request):
  request_json = await request.json()
  try:
    transaction_uuid = request_json['transaction_uuid']
    device_uuid = request_json['device_uuid']
    encrypted_payload = request_json['encrypted_payload']
    notification_title = request_json['notification_title']
    notification_body = request_json['notification_body']
    redis_conn = request.app[REDIS][SERVICE]
    await keystore.add_transaction(redis_conn, transaction_uuid, device_uuid, encrypted_payload)
    data_message = {"transaction_uuid": transaction_uuid }
    push_notifications_service = request.app[PUSH][SERVICE]
    await push_notifications_service.notify_single_device(
        registration_id=device_uuid,
        message_title=notification_title,
        message_body=notification_body,
        data_message=data_message)
    return web.Response(status=201)
  except KeyError as ke:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError as te:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except FirebaseError as fe:
    return web.json_response(error_message("Error pushing notifications through Firebase"), status=500)
  except:
      return web.json_response(error_message("Error unknown"), status=500)


@routes.post('/pop_transaction_details')
async def pop_transaction_details(request):
  request_json = await request.json()
  try:
    transaction_uuid = request_json['transaction_uuid']
    device_uuid = request_json['device_uuid']
    redis_conn = request.app[REDIS][SERVICE]
    details = await keystore.pop_transaction_details(redis_conn, transaction_uuid, device_uuid)
    json_response = {"encrypted_payload": details}
    return web.json_response(json_response)
  except KeyError as ke:
    return web.json_response(error_message("Incorrect input parameters"), status=400)
  except TypeError as te:
    return web.json_response(error_message("Incorrect JSON content type"), status=400)
  except KeystoreFetchError as kfe:
    return web.json_response(error_message("Error retrieving transaciton details"), status=500)
  except:
    return web.json_response(error_message("Error unknown"), status=500)


def get_kms_parameter(param_name):
   ssm = boto3.client('ssm', region_name='us-east-2')
   response = ssm.get_parameters(Names=[param_name], WithDecryption=True)
   return response['Parameters'][0]['Value']


async def initialize_push_notifications(app):
  local = app[PUSH][LOCAL]
  if local:
    session = aiohttp.ClientSession()
    app[PUSH][SERVICE] = PushNotificationsService(session, debug=local)
  else:
    api_key = get_kms_parameter('fcm-server-key')
    app[PUSH][SERVICE] = PushNotificationsService(api_key=api_key, debug=local)


async def initialize_keystore(app):
  if app[REDIS][LOCAL]:
    app[REDIS][SERVICE] = await keystore.create_connection(event_loop=app.loop)
  else:
    host = get_kms_parameter('balance-bridge-redis-host')
    app[REDIS][SERVICE] = await keystore.create_connection(event_loop=app.loop, host=host)


async def close_keystore(app):
  app[REDIS][SERVICE].close()
  await app[REDIS][SERVICE].wait_closed()


async def close_push_notification_connection(app):
  await app[PUSH][SERVICE].session.close()


def main(): 
  parser = argparse.ArgumentParser()
  parser.add_argument('--redis-local', action='store_true')
  parser.add_argument('--push-local', action='store_true')
  args = parser.parse_args()

  app = web.Application()
  app[REDIS] = {LOCAL: args.redis_local}
  app[PUSH] = {LOCAL: args.push_local}
  app.on_startup.append(initialize_push_notifications)
  app.on_startup.append(initialize_keystore)
  app.on_cleanup.append(close_keystore)
  app.on_cleanup.append(close_push_notification_connection)
  app.router.add_routes(routes)
  asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
  web.run_app(app, port=5000)


if __name__ == '__main__':
  main()
