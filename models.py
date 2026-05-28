import json
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum

class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    THINKING = "thinking"  # для отображения размышлений в интерфейсе
    TOOL = "tool"

class Message:
    def __init__(self, role: Role, content: str, timestamp: datetime = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            role=Role(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )

class Conversation:
    def __init__(self, id: str = None, title: str = "Новый диалог"):
        self.id = id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.title = title
        self.messages: List[Message] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_message(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        result = []
        for msg in self.messages:
            if msg.role == Role.TOOL:
                # Превращаем tool в user-сообщение с пояснением
                result.append({"role": "user", "content": f"[Результат инструмента]: {msg.content}"})
            elif msg.role in (Role.USER, Role.ASSISTANT, Role.SYSTEM):
                result.append({"role": msg.role.value, "content": msg.content})
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        conv = cls(id=data["id"], title=data["title"])
        conv.created_at = datetime.fromisoformat(data["created_at"])
        conv.updated_at = datetime.fromisoformat(data["updated_at"])
        conv.messages = [Message.from_dict(m) for m in data["messages"]]
        return conv