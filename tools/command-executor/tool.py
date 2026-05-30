# tools/command-executor/tool.py

from tool_router import BaseTool
import subprocess
import shlex

class Tool(BaseTool):
    def get_manifest(self):
        return {
            "description": "Выполняет консольную команду и возвращает результат её работы.",
            "parameters": {
                "command": {
                    "type": "string",
                    "description": "Команда для выполнения (например, 'ls -la' или 'echo Hello')"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Максимальное время ожидания в секундах (опционально, по умолчанию None — бесконечно)"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Рабочая директория для выполнения команды (опционально)"
                },
                "shell": {
                    "type": "boolean",
                    "description": "Использовать ли оболочку (по умолчанию False — безопаснее, но для сложных команд может потребоваться True)"
                }
            }
        }

    def run(self, **kwargs):
        command = kwargs.get("command")
        if not command:
            return {"error": "Не указан параметр 'command'"}

        timeout = kwargs.get("timeout")
        working_dir = kwargs.get("working_dir")
        shell = kwargs.get("shell", False)

        try:
            # Запускаем команду с блокировкой потока
            result = subprocess.run(
                command if shell else shlex.split(command),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                shell=shell
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Команда не завершилась за {timeout} секунд",
                "returncode": None,
                "stdout": "",
                "stderr": ""
            }
        except FileNotFoundError as e:
            return {
                "success": False,
                "error": f"Команда не найдена: {str(e)}",
                "returncode": None,
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка при выполнении команды: {str(e)}",
                "returncode": None,
                "stdout": "",
                "stderr": ""
            }