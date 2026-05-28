import os
import importlib.util
import json
import re

class BaseTool:
    def get_manifest(self):
        raise NotImplementedError
    def run(self, **kwargs):
        raise NotImplementedError

class ToolRouter:
    def __init__(self, tools_dir="tools"):
        self.tools = {}
        self.tools_dir = tools_dir
        self._load_tools()

    def _load_tools(self):
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir)
        for folder in os.listdir(self.tools_dir):
            path = os.path.join(self.tools_dir, folder, "tool.py")
            if os.path.exists(path):
                spec = importlib.util.spec_from_file_location(folder, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                tool_instance = module.Tool()
                self.tools[folder] = tool_instance

    def get_system_prompt_extension(self):
        specs = {name: tool.get_manifest() for name, tool in self.tools.items()}
        return (
            f"\nДОСТУПНЫЕ ИНСТРУМЕНТЫ: {json.dumps(specs, ensure_ascii=False)}.\n"
            "Чтобы вызвать инструмент, используй формат:\n"
            "[TOOL_CALL]{\"name\": \"имя_инструмента\", \"args\": {\"параметр\": \"значение\"}}\n"
            "ВАЖНО: Весь вызов должен быть в одной строке. JSON должен быть валидным и завершённым.\n"
            "После закрывающей скобки } ничего не добавляй. Не используй закрывающий тег [/TOOL_CALL].\n"
            "Пример правильного вызова:\n"
            "[TOOL_CALL]{\"name\": \"text-editing\", \"args\": {\"action\": \"read\", \"file_path\": \"C:\\\\test.txt\"}}\n"
        )
        

    def parse_tool_call(self, text: str):
        """
        Ищет вызов инструмента в тексте.
        Поддерживает форматы:
        - [TOOL_CALL]{"name": "...", "args": {...}}
        - [TOOL_CALL]{"name": "...", "args": {...}}[/TOOL_CALL]
        - [TOOL_CALL]{"name": "...", "args": {...}} (с возможным обрывом)
        Возвращает (name, args, text_before_call, full_match_or_error)
        """
        # Ищем начало тега
        start_tag = "[TOOL_CALL]"
        start_pos = text.find(start_tag)
        if start_pos == -1:
            return None, None, text, None

        # Текст до вызова
        text_before = text[:start_pos]
        # Ищем конец JSON (сбалансированные фигурные скобки)
        json_start = start_pos + len(start_tag)
        brace_count = 0
        end_pos = -1
        in_string = False
        escape = False

        for i, ch in enumerate(text[json_start:], start=json_start):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1  # позиция после закрывающей скобки
                        break

        if end_pos == -1:
            # JSON не завершён – обрыв
            return None, None, text, "Ошибка: вызов инструмента незавершён (нет закрывающей скобки). Повтори вызов полностью."
        
        json_str = text[json_start:end_pos].strip()
        # Пропускаем возможный закрывающий тег после JSON
        remaining = text[end_pos:].lstrip()
        if remaining.startswith("[/TOOL_CALL]"):
            end_pos += len("[/TOOL_CALL]")  # съедаем закрывающий тег, но нам не важно

        try:
            call = json.loads(json_str)
            name = call.get("name")
            args = call.get("args", {})
            if not name:
                raise ValueError("Missing 'name' field")
        except (json.JSONDecodeError, ValueError) as e:
            return None, None, text, f"Ошибка парсинга JSON: {e}\nСырая строка: {json_str[:200]}"

        return name, args, text_before, json_str  # возвращаем успешный парсинг

    def execute(self, name, args):
        if name in self.tools:
            try:
                result = self.tools[name].run(**args)
                return result
            except Exception as e:
                return {"error": f"Ошибка при выполнении инструмента {name}: {str(e)}"}
        return {"error": f"Инструмент '{name}' не найден. Доступны: {list(self.tools.keys())}"}