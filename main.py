from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user.user_controller import user_router
from conversation.conversation_controller import conversation_router
from message.message_controller import message_router

app = FastAPI(
    title="OTT BACKEND",
    description="API Documentation",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def read_root():
    return {"message": "BACKEND RUNNING"}

app.include_router(
    router=user_router,
    prefix="/user",
    tags=["User Controller"]
)

app.include_router(
    router=conversation_router,
    prefix="/conversation",
    tags=["Conversation Controller"]
)

app.include_router(
    router=message_router,
    prefix="/message",
    tags=["Message Controller"]
)


