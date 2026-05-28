import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class LMStudioStreamWorker(QThread):
    status_changed = pyqtSignal(str)
    thinking_part = pyqtSignal(str)
    response_part = pyqtSignal(str)          # обычный текст (для потокового вывода)
    tool_call_detected = pyqtSignal(str, dict, str)  # (tool_name, args, text_before_call)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, conversation, config_manager=None, system_prompt=None, router=None):
        super().__init__()
        self.conversation = conversation
        self.system_prompt = system_prompt
        self.router = router
        self.api_url = config_manager.get("lm_studio.api_url")
        self.model = config_manager.get("lm_studio.model")
        self.temperature = config_manager.get("lm_studio.temperature", 0.2)
        self._stop = False
        self._full_response = ""   # накапливаем весь ответ модели

    def stop(self):
        self._stop = True

    def run(self):
        messages_history = [{"role": "system", "content": self.system_prompt}]
        for msg in self.conversation.messages:
            # Пропускаем thinking, tool – они не нужны для API
            if msg.role.value in ("user", "assistant", "system"):
                messages_history.append({"role": msg.role.value, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": messages_history,
            "temperature": self.temperature,
            "stream": True
        }

        try:
            response = requests.post(self.api_url, json=payload, stream=True, timeout=600)
            buffer = ""
            for line in response.iter_lines():
                if self._stop:
                    break
                if not line:
                    continue
                decoded = line.decode('utf-8').strip()
                if decoded.startswith("data: "):
                    decoded = decoded[6:].strip()
                if decoded == "[DONE]":
                    continue

                try:
                    data = json.loads(decoded)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "") or delta.get("reasoning_content", "")
                    if content:
                        buffer += content
                        self._full_response += content
                        # Потоково отправляем текст, НО если в будущем появится [TOOL_CALL], надо прекратить отправку
                        # Простейший способ: проверять, нет ли в накопленном буфере начала маркера
                        if "[TOOL_CALL]" not in buffer:
                            self.response_part.emit(content)
                        else:
                            # Если маркер начался, не отправляем этот кусок – он будет частью вызова
                            pass
                except Exception:
                    continue

            # Стрим закончился – проверяем, есть ли вызов инструмента
            # Стрим закончился – проверяем наличие вызова
            if self.router and self._full_response:
                name, args, text_before, result = self.router.parse_tool_call(self._full_response)
                if isinstance(result, str) and "Ошибка" in result:
                    # Ошибка парсинга или обрыв
                    self.response_part.emit(result)
                elif name is not None:
                    # Валидный вызов
                    self.tool_call_detected.emit(name, args, text_before)
                else:
                    # Нет вызова – просто выводим весь ответ, если ещё не вывели
                    # (но мы уже выводили частями, возможно, что-то осталось после маркера? Нет, т.к. маркера нет)
                    pass

            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))