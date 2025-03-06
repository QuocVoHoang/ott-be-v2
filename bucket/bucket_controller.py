from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Conversation, User, ConversationParticipant
from interface.interface import (
  INewConversationData, 
  IUpdateConversationAvatarData, 
  IUpdateConversationNameData, 
  IUpdateConversationParticipantData,
  IRemoveParticipantData
)
from sqlalchemy.future import select
import datetime
from database import get_db
from fastapi import FastAPI, File, UploadFile
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

s3_client = boto3.client(
  "s3",
  aws_access_key_id=AWS_ACCESS_KEY,
  aws_secret_access_key=AWS_SECRET_KEY,
  region_name=AWS_REGION
)

s3_router = APIRouter()

@s3_router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
  try:
    file_content = await file.read()
    s3_client.put_object(
      Bucket=S3_BUCKET_NAME, 
      Key=file.filename, 
      Body=file_content,
    )

    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file.filename}"
    return {"filename": file.filename, "url": file_url}
  except Exception as e:
    return {"error": str(e)}


@s3_router.get("/download/{filename}")
async def download_file(filename: str):
  try:
    file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"
    return {"file_url": file_url}
  except Exception as e:
    return {"error": str(e)}


@s3_router.delete("/delete/{filename}")
async def delete_file(filename: str):
  try:
    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=filename)
    return {"message": f"{filename} deleted successfully"}
  except Exception as e:
    return {"error": str(e)}

