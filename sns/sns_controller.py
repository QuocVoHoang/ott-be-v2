from fastapi import APIRouter, Depends, HTTPException
import boto3
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from sqlalchemy.future import select
from models.models import User
import datetime
import pytz
from utils.utils import get_vn_time
from datetime import timedelta

load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_ARN = os.getenv('AWS_ARN')
SECRET_KEY = "quoc_secret_key"
from authlib.jose import jwt

sns_client = boto3.client(
  'sns',
  region_name=AWS_REGION,
  aws_access_key_id=AWS_ACCESS_KEY,
  aws_secret_access_key=AWS_SECRET_KEY
)

sns_router = APIRouter()

class SMSRequest(BaseModel):
  phone_number: str
  message: str

class EmailRequest(BaseModel):
  email: str
  message: str
  subject: str = "Notification from FastAPI App"
  
def get_vietnam_now():
  utc_now = datetime.datetime.utcnow()
  vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
  vietnam_now = utc_now.replace(tzinfo=pytz.utc).astimezone(vietnam_tz)
  return vietnam_now.replace(tzinfo=None)
    
@sns_router.post("/send-sms/")
async def send_sms(data: SMSRequest, db: AsyncSession = Depends(get_db)):
  try:
    result = await db.execute(select(User).where(User.email == data.phone_number))
    user = result.scalars().first()
  
    if user:
      payload = {
        "sub": user.id,
        "email": user.email,
        "exp": await get_vn_time() + timedelta(hours=24)
      }
      token = jwt.encode({"alg": "HS256"}, payload, SECRET_KEY)
      return {"access_token": token, "token_type": "bearer"}
  
    response = sns_client.publish(
      PhoneNumber=data.phone_number,
      Message=data.message
    )
    return {"status": "SMS sent", "otp": data.message}
  except Exception as e:
    return {"error": str(e)}


@sns_router.post("/send-email/")
async def send_email(data: EmailRequest, db: AsyncSession = Depends(get_db)):
  try:
    print('data.email', data.email)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if user:
      print('existing_user', user.email)
      return {"message": "Email already registered!"}
    
    # Optional: kiểm tra nếu email chưa được subscribe
    subscriptions = sns_client.list_subscriptions_by_topic(TopicArn=AWS_ARN)
    already_subscribed = any(sub['Endpoint'] == data.email for sub in subscriptions['Subscriptions'])

    if not already_subscribed:
      sns_client.subscribe(
        TopicArn=AWS_ARN,
        Protocol='email',
        Endpoint=data.email
      )
      return {
        "status": "Subscription request sent. Please confirm via email."
      }

    # Nếu đã subscribe, thì gửi email
    response = sns_client.publish(
      TopicArn=AWS_ARN,
      Message=data.message,
      Subject=data.subject
    )
    
    return {"status": "Email sent", "response": response}
  except Exception as e:
    return {"error": str(e)}