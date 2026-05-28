import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class LMStudioStreamWorker(QThread):
    status_changed = pyqtSignal(str)
    thinking_part = pyqtSignal(str)
    response_part = pyqtSignal(str)          # Обычный текст для UI
    # Сигнал теперь передает: (список_тулов, чистый_текст_до_тулов)
    tool_calls_detected = pyqtSignal(list, str)  
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
        self._full_response = ""   
        self._emitted_len = 0      # Сколько символов мы уже успешно отправили в UI

    def stop(self):
        self._stop = True

    def run(self):
        messages_history = [{"role": "system", "content": self.system_prompt}]
        for msg in self.conversation.messages:
            if msg.role.value in ("user", "assistant", "system"):
                messages_history.append({"role": msg.role.value, "content": msg.content})
            elif msg.role.value == "tool":
                # ВАЖНО: Передаем результаты прошлых тулов как контекст, иначе модель их не увидит!
                messages_history.append({
                    "role": "user", 
                    "content": f"[РЕЗУЛЬТАТ ВЫЗОВА ИНСТРУМЕНТА]:\n{msg.content}"
                })

        payload = {
            "model": self.model,
            "messages": messages_history,
            "temperature": self.temperature,
            "stream": True
        }

        try:
            response = requests.post(self.api_url, json=payload, stream=True, timeout=600)
            self._emitted_len = 0
            self._full_response = ""
            
            tag = "[TOOL_CALL]"

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
                        self._full_response += content
                        
                        tag = "<tool_calls>"
                        # Проверяем, появился ли тег вызова в ответе
                        if tag in self._full_response:
                            tag_pos = self._full_response.find(tag)
                            json_start = self._full_response.find("{", tag_pos + len(tag))
                            
                            if json_start != -1:
                                # Проверяем, реальный ли это вызов (между тегом и { нет текста)
                                between = self._full_response[tag_pos + len(tag):json_start].strip()
                                if between == "":
                                    # Это реальный вызов инструмента — скрываем его из UI
                                    if tag_pos > self._emitted_len:
                                        self.response_part.emit(self._full_response[self._emitted_len:tag_pos])
                                        self._emitted_len = tag_pos
                                    continue
                        
                        # Защита от разрезания тега <tool_calls> на границе чанков
                        is_partial = False
                        for i in range(len(tag) - 1, 0, -1):
                            if self._full_response.endswith(tag[:i]):
                                is_partial = True
                                break
                        
                        # Если тег сейчас не режется пополам, отправляем накопленный текст в UI
                        if not is_partial:
                            text_to_send = self._full_response[self._emitted_len:]
                            if text_to_send:
                                self.response_part.emit(text_to_send)
                                self._emitted_len = len(self._full_response)
                                
                except Exception:
                    continue

            # Стрим ПОЛНОСТЬЮ завершился. Начинаем разбор полетов.
            if self.router and self._full_response:
                tool_calls, text_before = self.router.parse_all_tool_calls(self._full_response)
                
                if tool_calls:
                    # Модель вызвала один или несколько инструментов
                    self.tool_calls_detected.emit(tool_calls, text_before)

            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))