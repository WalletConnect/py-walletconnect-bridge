import aiohttp
import json

from wallet_connect.errors import FirebaseError

class PushNotificationsService(object):


  def __init__(self, session=None, api_key='dummy_api_key', debug=False):
    self.session = session
    self.api_key = api_key
    self.debug = debug
    self.fcm_endpoint = 'https://fcm.googleapis.com/fcm/send'


  async def notify_single_device(self, registration_id, message_title,
                                 message_body, data_message):
    if self.debug:
      print(data_message)
      return True
    payload = self.generate_payload(registration_id, message_title,
                                    message_body, data_message)
    response = await self.notify(payload)
    await self.parse_response(response)


  def generate_payload(self, registration_id, message_title, 
                       message_body, data_message):
    fcm_payload = {}
    fcm_payload['to'] = registration_id
    fcm_payload['android'] = dict(priority='high')
    fcm_payload['data'] = data_message
    fcm_payload['notification'] = {}
    fcm_payload['notification']['title'] = message_title
    fcm_payload['notification']['body'] = message_body
    return fcm_payload


  def request_headers(self):
    return {
        'Content-Type': 'application/json',
        'Authorization': 'key={}'.format(self.api_key),
    }


  async def notify(self, payload):
    headers = self.request_headers()
    resp = await self.session.post(self.fcm_endpoint, json=payload, headers=headers)
    return resp


  async def parse_response(self, response):
    if response.status != 200:
      raise FirebaseError("FCM server error")
    json_body = await response.json()
    success = json_body.get('success', 0)
    if not success:
      raise FirebaseError("FCM server error, push notification failed")
