from pyfcm import FCMNotification

class PushNotificationsService(object):

  def __init__(self, api_key='dummy_api_key', debug=False):
    self.push_notifications_service = FCMNotification(api_key=api_key)
    self.debug = debug

  async def notify(self, registration_id, message_title, message_body, data_message):
    if self.debug:
      print(data_message)
      return
    status = push_notifications_service.notify_single_device(
        registration_id=device_uuid, 
        message_title=message_title,
        message_body=message_body,
        data_message=data_message)
    if not status:
      raise FirebaseError

