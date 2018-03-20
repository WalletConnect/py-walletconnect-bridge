import aiohttp
import json

class PushNotificationsService(object):

  FCM_END_POINT = 'https://fcm.googleapis.com/fcm/send'

  def __init__(self, session=None, api_key='dummy_api_key', debug=False):
    self.session = session
    self.api_key = api_key
    self.debug = debug


  async def notify_single_device(self, registration_id, message_title,
                                 message_body, data_message):
    if self.debug:
      print(data_message)
      return True
    payload = self.generate_payload(registration_id, message_title,
                                    message_body, data_message)
    resp = await self.notify(payload)
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
    print('fcm headers: {}'.format(headers))
    print('push notification payload: {}'.format(payload))
    try:
      resp = await self.session.post(FCM_END_POINT, json=payload, headers=headers)
    except Exception as e:
      print(repr(e))
    print('response is...')
    print(resp)
    return resp


  async def parse_response(self, response):
    if response.status == 200:
      raise FirebaseError("FCM server error")
    if 'content-length' in response.headers and int(response.headers['content-length']) <= 0:
      raise FirebaseError("FCM server connection error, the response is empty")
    json_body = await resp.json()
    print('fcm response: {}'.format(json_body))
    success = json_body.get('success', False)
    if not success:
      raise FirebaseError("FCM server error, push notification failed")
