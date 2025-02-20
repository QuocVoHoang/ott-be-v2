from enum import Enum

class ConversationType(str, Enum):
  PRIVATE = "private"
  GROUP = "group"

class MessageType(str, Enum):
  TEXT = "text"
  IMAGE = "image"
  FILE = "file"
  AUDIO = "audio"
  VIDEO = "video"
