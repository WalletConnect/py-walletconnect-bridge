from flask import Flask, request, jsonify, abort
from flask_api import status

from balance_bridge import keystore
from balance_bridge.keystore import KeystoreWriteError, KeystoreFetchError

app = Flask(__name__)

# TODO unify response pattern

@app.errorhandler(400)
def bad_request_handler(error):
  message = {'message': repr(error)}
  return jsonify(message), status.HTTP_400_BAD_REQUEST


@app.errorhandler(500)
def internal_server_error_handler(error):
  message = {'message': repr(error)}
  return jsonify(message), status.HTTP_500_INTERNAL_SERVER_ERROR


@app.route('/register_push_notifications', methods=['PUT'])
def register_push_notifications():
  request_json = request.get_json()
  try:
    device_uuid = request_json['device_uuid']
  except (KeyError, TypeError) as kte:
    return bad_request_handler(kte)
  except Exception as e:
    return internal_server_error_handler(e)
  # TODO: register push notifications
  return '', status.HTTP_202_ACCEPTED


@app.route('/create_shared_connection', methods=['PUT'])
def create_shared_connection():
  request_json = request.get_json()
  try:
    token = request_json["token"]
    keystore.add_shared_connection(token)
  except (KeyError, TypeError) as kte:
    return bad_request_handler(kte)
  except (KeystoreWriteError, Exception) as e:
    return internal_server_error_handler(e)
  return '', status.HTTP_201_CREATED


@app.route('/update_connection_details', methods=['POST'])
def update_connection_details():
  request_json = request.get_json()
  try:
    token = request_json['token']
    encrypted_payload = request_json['encrypted_payload']
    keystore.update_connection_details(token, encrypted_payload)
  except (KeyError, TypeError) as kte:
    return bad_request_handler(kte)
  except (KeystoreWriteError, Exception) as e:
    return internal_server_error_handler(e)
  return '', status.HTTP_202_ACCEPTED


@app.route('/pop_connection_details', methods=['POST'])
def pop_connection_details():
  request_json = request.get_json()
  try:
    token = request_json['token']
    connection_details = keystore.pop_connection_details(token)
    if connection_details:
      json_response = {"encrypted_payload": connection_details}
      return jsonify(json_response), status.HTTP_200_OK
    else: 
      return '', status.HTTP_204_NO_CONTENT
  except (KeyError, TypeError) as kte:
    return bad_request_handler(kte)
  except Exception as e:
    return internal_server_error_handler(e)


@app.route('/initiate_transaction', methods=['PUT'])
def initiate_transaction():
  request_json = request.get_json()
  try:
    transaction_uuid = request_json['transaction_uuid']
    device_uuid = request_json['device_uuid']
    encrypted_payload = request_json['encrypted_payload']
    keystore.add_transaction(transaction_uuid, device_uuid, encrypted_payload)
  except (KeyError, TypeError) as kte:
    return bad_request_handler(kte)
  except Exception as e:
    return internal_server_error_handler(e)
  # TODO: server sends push notification to mobile client given by device UUID with data being transaction UUID
  return '', status.HTTP_201_CREATED


@app.route('/pop_transaction_details', methods=['POST'])
def pop_transaction_details():
  request_json = request.get_json()
  try:
    transaction_uuid = request_json['transaction_uuid']
    device_uuid = request_json['device_uuid']
    details = keystore.pop_transaction_details(transaction_uuid, device_uuid)
    json_response = {"encrypted_payload": details}
    return jsonify(json_response), status.HTTP_200_OK
  except (KeyError, TypeError) as kte:
    return bad_request_handler(kte)
  except (KeystoreFetchError, Exception) as e:
    return internal_server_error_handler(e)


def main(): 
  app.run(port=5000, debug=True)


if __name__ == '__main__':
  main()
