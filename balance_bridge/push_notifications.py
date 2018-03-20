import json

class PushNotificationsService(object):

  FCM_END_POINT = 'https://fcm.googleapis.com/v1/projects/balance-bridge/messages:send'

  def __init__(self, session, api_key='dummy_api_key', debug=False):
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
    print('push notification payload: {}'.format(payload))
    resp = await self.notify(payload)
    await self.parse_response(response)


  def generate_payload(self, registration_id, message_title, 
                       message_body, data_message):
    fcm_payload = dict()
    fcm_payload['to'] = registration_id
    fcm_payload['android'] = dict(priority='high')
    fcm_payload['data'] = data_message
    fcm_payload['notification'] = {}
    fcm_payload['notification']['title'] = message_title
    fcm_payload['notification']['body'] = message_body
    return json.dumps(fcm_payload)


  def request_headers(self):
    return {
        'Content-Type': 'application/json',
        'Authorization': 'key={}'.format(self.api_key),
    }


  async def notify(self, payload):
    headers = self.request_headers()
    print('fcm headers: {}'.format(headers))
    async with self.session.post(FCM_END_POINT, json=payload, 
                                 headers=headers) as resp:
      if 'Retry-After' in resp.headers and int(resp.headers['Retry-After']) > 0:
        print('retry...')
        sleep_time = int(resp.headers['Retry-After'])
        await asyncio.sleep(sleep_time)
        return await self.notify(payload)
      else:
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
