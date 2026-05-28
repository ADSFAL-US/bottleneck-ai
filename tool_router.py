import os
import importlib.util
import json

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
            "Чтобы вызвать инструмент, используй НАТИВНЫЙ формат строго в самом конце своего ответа:\n"
            "<tool_calls>\n"
            "<name>имя_инструмента</name>\n"
            "<args>{\"параметр\": \"значение\"}</args>\n"
            "</tool_calls>\n"
            "ВАЖНО:\n"
            "1. Если у инструмента нет параметров, внутри тега <args> должен быть пустой JSON-объект: <args>{}</args>.\n"
            "2. Вызов инструмента должен быть самым финальным действием. Никакого текста после закрывающего тега </tool_calls> быть не должно."
        )

    def parse_all_tool_calls(self, text: str):
        """
        Ищет все вызовы инструментов в нативном XML-формате модели.
        Устойчив к отсутствию закрывающих тегов при обрыве генерации.
        """
        import re
        tool_calls = []
        tag = "<tool_calls>"
        
        # Отрезаем чистый текст до первого вызова инструмента для вывода в UI
        first_tag_pos = text.find(tag)
        text_before = text if first_tag_pos == -1 else text[:first_tag_pos]
        
        # Находим все блоки <tool_calls>...</tool_calls> (или до конца текста, если тег не закрыт)
        pattern = r"<tool_calls>(.*?)(?:</tool_calls>|$)"
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            block_content = match.group(1).strip()
            raw_chunk = match.group(0)
            if not block_content:
                continue
                
            # Извлекаем имя инструмента из <name>...</name>
            name_match = re.search(r"<name>(.*?)</name>", block_content, re.DOTALL)
            if not name_match:
                # Фоллбэк: если генерация оборвалась прямо внутри тега name
                name_match = re.search(r"<name>([a-zA-Z0-9_-]+)", block_content)
                
            if name_match:
                name = name_match.group(1).strip()
                args = {}
                
                # Извлекаем аргументы из <args>...</args>
                args_match = re.search(r"<args>(.*?)</args>", block_content, re.DOTALL)
                if not args_match:
                    # Фоллбэк на случай обрыва строки на закрывающем теге args
                    args_match = re.search(r"<args>(\{.*\}?)", block_content, re.DOTALL)
                    
                if args_match:
                    args_str = args_match.group(1).strip()
                    if args_str and args_str != "{}":
                        try:
                            args = json.loads(args_str)
                        except Exception:
                            # Если JSON побился при стриминге, отдаем как сырую строку
                            args = {"raw_args": args_str}
                            
                tool_calls.append((name, args, raw_chunk, None))
            else:
                tool_calls.append((None, None, raw_chunk, "Ошибка: Не удалось распознать имя инструмента в <tool_calls>"))
                
        return tool_calls, text_before

    def execute(self, name, args):
        if name in self.tools:
            try:
                # Проверяем, что args — это словарь, иначе берем пустой dict
                actual_args = args if isinstance(args, dict) else {}
                # Распаковываем его прямо в именованные аргументы метода run()
                result = self.tools[name].run(**actual_args)
                return result
            except Exception as e:
                return {"error": f"Ошибка при выполнении инструмента {name}: {str(e)}"}
        return {"error": f"Инструмент '{name}' не найден. Доступны: {list(self.tools.keys())}"}