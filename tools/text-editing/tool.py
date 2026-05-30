# tools/text-editing/tool.py

from tool_router import BaseTool
import os

class Tool(BaseTool):
    def get_manifest(self):
        return {
            "description": "Чтение и запись текстовых файлов. Поддерживает чтение диапазона строк, запись в конец, замену строки или подстроки.",
            "parameters": {
                "action": {"type": "string", "enum": ["read", "write"], "description": "Действие: read или write"},
                "file_path": {"type": "string", "description": "Путь к файлу"},
                "text": {"type": "string", "description": "Текст для записи (только для write)"},
                "start_line": {"type": "integer", "description": "Номер строки для начала чтения/записи (1-индексация, опционально)"},
                "end_line": {"type": "integer", "description": "Номер строки для конца чтения (только для read, опционально)"},
                "replace_text": {"type": "string", "description": "Текст для замены (только для write, опционально)"}
            }
        }

    def run(self, **kwargs):
        action = kwargs.get("action")
        if not action:
            return {"error": "Не указано поле 'action'. Допустимые значения: read, write"}

        if action == "read":
            return self._read_file(
                kwargs.get("file_path"),
                kwargs.get("start_line"),
                kwargs.get("end_line")
            )
        elif action == "write":
            return self._write_file(
                kwargs.get("file_path"),
                kwargs.get("text", ""),
                kwargs.get("start_line"),
                kwargs.get("replace_text")
            )
        else:
            return {"error": f"Неизвестное действие: {action}. Допустимо: read, write"}

    def _read_file(self, file_path, start_line, end_line):
        if not file_path:
            return {"error": "Не указан file_path"}

        if not os.path.exists(file_path):
            return {"error": f"Файл не найден: {file_path}"}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            return {"error": f"Ошибка чтения файла: {str(e)}"}

        total = len(lines)

        # Определяем диапазон (1-индексация)
        if start_line is None and end_line is None:
            first, last = 1, total
        elif start_line is not None and end_line is None:
            first, last = start_line, total
        elif start_line is None and end_line is not None:
            first, last = 1, end_line
        else:
            first, last = start_line, end_line

        if first < 1:
            return {"error": f"start_line не может быть меньше 1: {first}"}
        if last < 1:
            return {"error": f"end_line не может быть меньше 1: {last}"}
        if first > last:
            return {"error": f"start_line ({first}) больше end_line ({last})"}
        if first > total:
            return {"result": ""}  # Диапазон за пределами файла

        start_idx = first - 1
        end_idx = min(last, total) - 1

        result_lines = []
        for i in range(start_idx, end_idx + 1):
            line_content = lines[i].rstrip("\n")
            result_lines.append(f"{i+1}: {line_content}")

        return {"result": "\n".join(result_lines)}

    def _write_file(self, file_path, text, start_line, replace_text):
        if not file_path:
            return {"error": "Не указан file_path"}

        # Режим замены подстроки
        if replace_text is not None:
            if not os.path.exists(file_path):
                return {"error": f"Файл не найден: {file_path}"}
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                pos = content.find(replace_text)
                if pos == -1:
                    return {"error": f"Текст для замены не найден: {replace_text}"}
                new_content = content[:pos] + text + content[pos + len(replace_text):]
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return {"result": "Текст успешно заменён"}
            except Exception as e:
                return {"error": f"Ошибка при замене текста: {str(e)}"}

        # Если start_line не указан — дописываем в конец (или создаём файл)
        if start_line is None:
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(text)
                if not os.path.exists(file_path):
                    return {"result": f"Файл создан и текст записан: {file_path}"}
                else:
                    return {"result": f"Текст добавлен в конец файла: {file_path}"}
            except Exception as e:
                return {"error": f"Ошибка при записи в конец файла: {str(e)}"}

        # Режим записи/замены начиная с определённой строки
        try:
            # Читаем существующий файл или создаём пустой список
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            else:
                lines = []

            idx = start_line - 1
            if idx < 0:
                return {"error": f"start_line должен быть >= 1, получено {start_line}"}

            insert_lines = text.splitlines()
            insert_lines_with_newline = [line + "\n" for line in insert_lines]
            if not insert_lines_with_newline and text.endswith("\n"):
                insert_lines_with_newline.append("\n")

            if idx >= len(lines):
                lines.extend(["\n"] * (idx - len(lines)))
                lines.extend(insert_lines_with_newline)
            else:
                lines = lines[:idx] + insert_lines_with_newline

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return {"result": f"Текст записан начиная со строки {start_line}"}
        except Exception as e:
            return {"error": f"Ошибка при записи файла: {str(e)}"}