import time

def now():
  now = time.time()
  return now

def get_expiration_time(ttl_in_seconds):
  expires = int(time.time() + ttl_in_seconds) * 1000
  return expires
