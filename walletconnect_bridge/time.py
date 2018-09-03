import time

def now():
  now = time.time()
  return now

def get_expiration_time(ttl_in_seconds):
  expires_in_seconds = time.time() + ttl_in_seconds
  return expires_in_seconds
