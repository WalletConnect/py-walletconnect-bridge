import sys
import argparse

from aiohttp import web
import boto3

from balance_bridge.keystore import RedisKeystore
from balance_bridge.push_notifications import PushNotificationsService
from balance_bridge.errors import KeystoreWriteError, KeystoreFetchError, FirebaseError, KeystoreTokenExpiredError

routes = web.RouteTableDef()

def error_message(message):
  return {"message": message}


@routes.get('/hello')
async def hello(request):
  return web.Response(text="hello world")


@routes.put('/create_shared_connection')
async def create_shared_connection(request):
  request_json = await request.json()
  try:
    token = request_json["token"]
    keystore = request.app['io.balance.bridge.keystore']
    keystore.add_shared_connection(token)
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
    keystore = request.app['io.balance.bridge.keystore']
    keystore.update_connection_details(token, encrypted_payload)
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
    keystore = request.app['io.balance.bridge.keystore']
    connection_details = keystore.pop_connection_details(token)
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
    keystore = request.app['io.balance.bridge.keystore']
    details = keystore.pop_transaction_details(transaction_uuid, device_uuid)
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


def initialize_push_notifications(debug=False):
  if not debug:
    api_key = get_kms_parameter('fcm-server-key')
    return PushNotificationsService(api_key=api_key, debug=debug)
  return PushNotificationsService(debug=debug)


def initialize_keystore(debug=False):
  if not debug:
    host = get_kms_parameter('balance-bridge-redis-host')
    return RedisKeystore(host=host)
  return RedisKeystore()


def main(): 
  app = web.Application()
  parser = argparse.ArgumentParser()
  parser.add_argument('--redis-local', action='store_true')
  parser.add_argument('--push-local', action='store_true')
  args = parser.parse_args()
  app['io.balance.bridge.push_notifications_service'] = initialize_push_notifications(args.push_local)
  app['io.balance.bridge.keystore'] = initialize_keystore(args.redis_local)
  app.router.add_routes(routes)
  web.run_app(app, port=5000)


if __name__ == '__main__':
  main()
