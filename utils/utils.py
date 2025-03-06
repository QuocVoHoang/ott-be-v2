import datetime
import pytz

async def get_vn_time():
  utc_now = datetime.datetime.utcnow()
  vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
  vietnam_now = utc_now.replace(tzinfo=pytz.utc).astimezone(vietnam_tz)
  vietnam_now_naive = vietnam_now.replace(tzinfo=None)
  
  return vietnam_now_naive