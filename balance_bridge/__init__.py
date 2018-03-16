import sys
import argparse

from aiohttp import web
import boto3

from balance_bridge.keystore import KeyValueStore
from balance_bridge.push_notifications import PushNotificationsService
from balance_bridge.errors import KeystoreWriteError, KeystoreFetchError, FirebaseError

routes = web.RouteTableDef()

@routes.put('/create_shared_connection')
async def create_shared_connection(request):
  request_json = await request.json()
  try:
    token = request_json["token"]
    keystore = request.app['io.balance.bridge.keystore']
    keystore.add_shared_connection(token)
  except (KeyError, TypeError):
    raise web.HTTPBadRequest
  except (KeystoreWriteError, Exception):
    raise web.HTTPInternalServerError
  return web.Response(status=201)


@routes.post('/update_connection_details')
async def update_connection_details(request):
  request_json = await request.json()
  try:
    token = request_json['token']
    encrypted_payload = request_json['encrypted_payload']
    keystore = request.app['io.balance.bridge.keystore']
    keystore.update_connection_details(token, encrypted_payload)
  except (KeyError, TypeError):
    raise web.HTTPBadRequest
  except (KeystoreWriteError, Exception):
    raise web.HTTPInternalServerError
  return web.Response(status=202)


@routes.post('/pop_connection_details')
async def pop_connection_details(request):
  request_json = await request.json()
  try:
    token = request_json['token']
    keystore = request.app['io.balance.bridge.keystore']
    connection_details = keystore.pop_connection_details(token)
    if connection_details:
      json_response = {"encrypted_payload": connection_details}
      return web.json_response(json_response)
    else: 
      return web.Response(status=204)
  except (KeyError, TypeError):
    raise web.HTTPBadRequest
  except Exception:
    raise web.HTTPInternalServerError


@routes.put('/initiate_transaction')
async def initiate_transaction(request):
  request_json = await request.json()
  try:
    transaction_uuid = request_json['transaction_uuid']
    device_uuid = request_json['device_uuid']
    encrypted_payload = request_json['encrypted_payload']
    keystore = request.app['io.balance.bridge.keystore']
    keystore.add_transaction(transaction_uuid, device_uuid, encrypted_payload)
    data_message = {"transaction_uuid": transaction_uuid }
    push_notifications_service = request.app['io.balance.bridge.push_notifications_service']
    push_notifications_service.notify(
        registration_id=device_uuid,
        message_title='Balance Manager',
        message_body='Confirm your transaction',
        data_message=data_message)
    return web.Response(status=201)
  except (KeyError, TypeError):
    raise web.HTTPBadRequest
  except (FirebaseError, Exception):
    raise web.HTTPInternalServerError


@routes.post('/pop_transaction_details')
async def pop_transaction_details(request):
  request_json = await request.json()
  try:
    transaction_uuid = request_json['transaction_uuid']
    device_uuid = request_json['device_uuid']
    keystore = request.app['io.balance.bridge.keystore']
    details = keystore.pop_transaction_details(transaction_uuid, device_uuid)
    json_response = {"encrypted_payload": details}
    return web.json_response(json_response)
  except (KeyError, TypeError):
    raise web.HTTPBadRequest
  except (KeystoreFetchError, Exception):
    raise web.HTTPInternalServerError


def initialize_push_notifications(debug=False):
  api_key = "api_key"
  if not debug:
    api_key_response = boto3_client.get_parameter(Name='firebase_api_key',
                                                  WithDecryption=True)
    api_key = api_key_response['Parameter']['Value']
  return PushNotificationsService(api_key=api_key, debug=debug)


def initialize_key_value_store(debug=False):
  if not debug:
    redis_host_response = boto3_client.get_parameter(Name='redis_host',
                                                     WithDecryption=False)
    host = redis_host_response['Parameter']['Value']
    return KeyValueStore(host=host)
  else:
    return KeyValueStore()


def main(): 
  app = web.Application()
  parser = argparse.ArgumentParser()
  parser.add_argument('--debug', action='store_true')
  args = parser.parse_args()
  if not args.debug:
    app['io.balance.bridge.boto3_client'] = boto3.client('ssm')
  app['io.balance.bridge.push_notifications_service'] = initialize_push_notifications(args.debug)
  app['io.balance.bridge.keystore'] = initialize_key_value_store(args.debug)
  app.router.add_routes(routes)
  web.run_app(app, port=5000)


if __name__ == '__main__':
  main()
