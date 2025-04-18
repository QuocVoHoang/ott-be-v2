from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time
from typing import Dict, Set
from agora_token_builder import RtcTokenBuilder
import os
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("APP_ID")
APP_CERTIFICATE = os.getenv("APP_CERTIFICATE")

call_router = APIRouter()

TOKEN_EXPIRATION_SEC = 600

rooms_db: Dict[str, Set[int]] = {}

class TokenRequest(BaseModel):
    channel_name: str
    uid: int

class LeaveRoomRequest(BaseModel):
    channel_name: str
    uid: int

@call_router.post("/agora/token")
def get_agora_token(req: TokenRequest):
    channel = req.channel_name
    uid = req.uid

    if not APP_ID or not APP_CERTIFICATE:
        raise HTTPException(status_code=500, detail="Thiếu cấu hình APP_ID hoặc APP_CERTIFICATE")

    if channel not in rooms_db:
        rooms_db[channel] = set()
    rooms_db[channel].add(uid)

    expire_at = int(time.time()) + TOKEN_EXPIRATION_SEC
    role = 1
    token = RtcTokenBuilder.buildTokenWithUid(
        APP_ID,
        APP_CERTIFICATE,
        channel,
        uid,
        role,
        expire_at
    )

    return {
        "token": token,
        "appId": APP_ID,
        "channelName": channel,
        "uid": uid,
        "expireAt": expire_at
    }

@call_router.post("/agora/leave")
def leave_room(req: LeaveRoomRequest):
    channel = req.channel_name
    uid = req.uid

    if channel not in rooms_db:
        raise HTTPException(status_code=404, detail="Phòng không tồn tại")

    if uid in rooms_db[channel]:
        rooms_db[channel].remove(uid)

    if len(rooms_db[channel]) == 0:
        del rooms_db[channel]

    return {"detail": f"Người dùng {uid} đã rời phòng {channel}"}