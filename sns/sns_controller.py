from fastapi import APIRouter
import boto3
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_ARN = os.getenv('AWS_ARN')

sns_client = boto3.client('sns', region_name=AWS_REGION)

sns_router = APIRouter()

@sns_router.get('/')
async def health():
  return 'health'

class Notification(BaseModel):
  message: str
    
@sns_router.post("/send-notification/")
async def send_notification(notification: Notification):
  try:
    response = sns_client.publish(
      TopicArn=AWS_ARN,
      Message=notification.message
    )
    return {
      "status": "success",
      "message_id": response['MessageId'],
      "message": f"Notification sent: {notification.message}"
    }
  except Exception as e:
    return {"status": "error", "message": str(e)}