# tools/text-editing/tool.py

import os

class Tool:
    def __init__(self):
        pass

    # ============== Чтение ==============
    def read_file(self, file_path, start_line=None, end_line=None):
        if not os.path.exists(file_path):
            return {"error": f"Файл не найден: {file_path}"}

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Определяем диапазон строк (1-индексация)
        if start_line is None and end_line is None:
            first, last = 0, total_lines - 1
        elif start_line is not None and end_line is None:
            first, last = start_line - 1, total_lines - 1
        elif start_line is None and end_line is not None:
            first, last = 0, end_line - 1
        else:
            first, last = start_line - 1, end_line - 1

        if first < 0 or last < 0:
            return {"error": "Некорректный диапазон строк"}

        if first > total_lines:
            return {"result": ""}

        if first > last:
            return {"error": f"Некорректный диапазон: start_line={start_line}, end_line={end_line}"}

        result = []
        for idx in range(first, min(last, total_lines - 1) + 1):
            line_content = lines[idx].rstrip("\n")
            result.append(f"{idx+1}: {line_content}")

        return {"result": "\n".join(result)}

    # ============== Запись ==============
    def write_file(self, file_path, text, start_line=None, replace_text=None):
        # Режим замены подстроки
        if replace_text is not None:
            if not os.path.exists(file_path):
                return {"error": f"Файл не найден: {file_path}"}
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            pos = content.find(replace_text)
            if pos == -1:
                return {"error": f"Текст для замены не найден: {replace_text}"}
            new_content = content[:pos] + text + content[pos+len(replace_text):]
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"result": "Текст успешно заменён"}

        # Если файла нет — создать и записать
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            return {"result": f"Файл создан: {file_path}"}

        # Если start_line не указан — дописать в конец
        if start_line is None:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(text)
            return {"result": f"Текст добавлен в конец файла: {file_path}"}

        # Вставка начиная с определённой строки
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        idx = start_line - 1
        if idx < 0:
            return {"error": f"start_line должен быть >= 1, получено {start_line}"}

        insert_lines = text.splitlines()
        if idx >= len(lines):
            lines.extend(['\n'] * (idx - len(lines) + 1))
            lines[idx:] = [line + '\n' for line in insert_lines] + lines[idx:]
        else:
            lines = lines[:idx] + [line + '\n' for line in insert_lines] + lines[idx+1:]

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return {"result": f"Текст записан начиная со строки {start_line}"}

    # ============== Интерфейс для ToolRouter ==============
    def get_manifest(self):
        return {
            "name": "text-editing",
            "description": "Чтение и запись текстовых файлов с построчным контролем",
            "actions": {
                "read": {
                    "description": "Прочитать часть файла",
                    "parameters": {
                        "file_path": "путь к файлу",
                        "start_line": "номер первой строки (1-индексация, опционально)",
                        "end_line": "номер последней строки (опционально)"
                    }
                },
                "write": {
                    "description": "Записать текст в файл (дописать, вставить или заменить подстроку)",
                    "parameters": {
                        "file_path": "путь к файлу",
                        "text": "текст для записи",
                        "start_line": "строка для вставки (1-индексация, опционально)",
                        "replace_text": "искомый текст для замены (опционально)"
                    }
                }
            }
        }

    def run(self, **kwargs):
        action = kwargs.get("action")
        if not action:
            return {"error": "Не указано поле 'action' в аргументах"}

        if action == "read":
            return self.read_file(
                file_path=kwargs.get("file_path"),
                start_line=kwargs.get("start_line"),
                end_line=kwargs.get("end_line")
            )
        elif action == "write":
            return self.write_file(
                file_path=kwargs.get("file_path"),
                text=kwargs.get("text", ""),
                start_line=kwargs.get("start_line"),
                replace_text=kwargs.get("replace_text")
            )
        else:
            return {"error": f"Неизвестное действие: {action}. Допустимо: read, write"}