import os
import json
from typing import List, Optional
from models import Conversation
from config_manager import ConfigManager

class ConversationManager:
    def __init__(self):
        self.config = ConfigManager()
        self.conversations_dir = self.config.get("conversations_dir", "conversations")
        self._ensure_dir()
        self.conversations: List[Conversation] = []
        self.current_conversation: Optional[Conversation] = None

    def _ensure_dir(self):
        if not os.path.exists(self.conversations_dir):
            os.makedirs(self.conversations_dir)

    def _get_file_path(self, conv_id: str) -> str:
        return os.path.join(self.conversations_dir, f"{conv_id}.json")

    def load_all_conversations(self) -> List[Conversation]:
        self.conversations = []
        for filename in os.listdir(self.conversations_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.conversations_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        conv = Conversation.from_dict(data)
                        self.conversations.append(conv)
                except Exception as e:
                    print(f"Ошибка загрузки диалога {filename}: {e}")
        # Сортировка по дате обновления (свежие сверху)
        self.conversations.sort(key=lambda x: x.updated_at, reverse=True)
        return self.conversations

    def save_conversation(self, conv: Conversation):
        filepath = self._get_file_path(conv.id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(conv.to_dict(), f, ensure_ascii=False, indent=2)

    def new_conversation(self, title: str = None) -> Conversation:
        conv = Conversation(title=title or "Новый диалог")
        self.conversations.insert(0, conv)
        self.current_conversation = conv
        self.save_conversation(conv)
        return conv

    def set_current_conversation(self, conv: Conversation):
        self.current_conversation = conv

    def add_message_to_current(self, message):
        if self.current_conversation:
            self.current_conversation.add_message(message)
            self.save_conversation(self.current_conversation)

    def delete_conversation(self, conv: Conversation):
        if conv == self.current_conversation:
            self.current_conversation = None
        if conv in self.conversations:
            self.conversations.remove(conv)
        filepath = self._get_file_path(conv.id)
        if os.path.exists(filepath):
            os.remove(filepath)