# tools/app_controller/tool.py
# Инструмент для управления приложениями Windows:
# - получение списка установленных приложений (аналог Win+S)
# - запуск приложения по имени

import subprocess
import json
import os
from tool_router import BaseTool

class Tool(BaseTool):
    """
    Инструмент позволяет получить список доступных приложений (из меню «Пуск»)
    и запустить любое из них.
    """

    def get_manifest(self):
        """
        Манифест инструмента: описание и схема параметров.
        """
        return {
            "description": (
                "Управление приложениями Windows. Позволяет получить список "
                "всех приложений, доступных через меню «Пуск» (аналог Win+S), "
                "и запустить выбранное приложение."
            ),
            "parameters": {
                "action": {
                    "type": "string",
                    "description": "Действие: 'list' — получить список приложений, 'launch' — запустить приложение",
                    "enum": ["list", "launch"]
                },
                "app_name": {
                    "type": "string",
                    "description": "Имя приложения для запуска (обязательно, если action='launch')"
                }
            }
        }

    def run(self, **kwargs):
        """
        Выполняет запрошенное действие.
        Для action='list' возвращает список приложений.
        Для action='launch' запускает приложение по имени.
        """
        action = kwargs.get("action")
        if action is None:
            return {"error": "Отсутствует обязательный параметр 'action'"}

        if action == "list":
            return self._list_apps()
        elif action == "launch":
            app_name = kwargs.get("app_name")
            if not app_name:
                return {"error": "Для запуска приложения укажите параметр 'app_name'"}
            return self._launch_app(app_name)
        else:
            return {"error": f"Недопустимое значение action: {action}. Допустимы: 'list', 'launch'"}

    # --------------------------------------------------------------------------
    # Вспомогательные методы
    # --------------------------------------------------------------------------

    def _list_apps(self):
        """
        Возвращает список приложений, собранных из стандартных папок меню «Пуск».
        Использует PowerShell для получения имён ярлыков.
        """
        ps_script = '''
        $paths = @(
            "$env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
            "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs"
        )
        $apps = @()
        foreach ($path in $paths) {
            if (Test-Path $path) {
                $shortcuts = Get-ChildItem -Path $path -Recurse -Filter *.lnk -ErrorAction SilentlyContinue
                foreach ($shortcut in $shortcuts) {
                    $name = [System.IO.Path]::GetFileNameWithoutExtension($shortcut.Name)
                    # Добавляем также путь относительно корня меню для удобства
                    $relative = $shortcut.FullName.Substring($path.Length + 1)
                    $relative = [System.IO.Path]::GetDirectoryName($relative)
                    if ($relative -and $relative -ne "") {
                        $display = "$name ($relative)"
                    } else {
                        $display = $name
                    }
                    $apps += $display
                }
            }
        }
        $apps = $apps | Sort-Object -Unique
        ConvertTo-Json -InputObject $apps -Compress
        '''
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                return {"error": f"Ошибка PowerShell: {error_msg}"}
            # Парсим JSON-массив
            apps = json.loads(result.stdout.strip())
            if not isinstance(apps, list):
                apps = [apps] if apps else []
            return {
                "success": True,
                "result": apps,
                "count": len(apps),
                "message": f"Найдено {len(apps)} приложений"
            }
        except subprocess.TimeoutExpired:
            return {"error": "Превышено время ожидания при получении списка приложений"}
        except json.JSONDecodeError as e:
            return {"error": f"Ошибка разбора ответа PowerShell: {str(e)}"}
        except Exception as e:
            return {"error": f"Неожиданная ошибка: {str(e)}"}

    def _launch_app(self, app_name):
        """
        Запускает приложение по имени.
        Ищет ярлык в папках меню «Пуск» (точное совпадение имени без расширения),
        затем извлекает целевой путь и запускает его.
        Если точное совпадение не найдено, пытается найти частичное совпадение.
        """
        ps_script = f'''
        $appName = "{app_name.Replace('"', '`"')}"
        $paths = @(
            "$env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
            "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs"
        )
        $found = $null
        foreach ($path in $paths) {{
            if (Test-Path $path) {{
                $shortcuts = Get-ChildItem -Path $path -Recurse -Filter *.lnk -ErrorAction SilentlyContinue
                foreach ($shortcut in $shortcuts) {{
                    $name = [System.IO.Path]::GetFileNameWithoutExtension($shortcut.Name)
                    if ($name -eq $appName) {{
                        $shell = New-Object -ComObject WScript.Shell
                        $lnk = $shell.CreateShortcut($shortcut.FullName)
                        $target = $lnk.TargetPath
                        $args = $lnk.Arguments
                        if ($target -and (Test-Path $target)) {{
                            $found = @{{ Target = $target; Arguments = $args }}
                            break
                        }}
                    }}
                }}
                if ($found) {{ break }}
            }}
        }}
        # Если точного совпадения нет, пробуем частичное
        if (-not $found) {{
            foreach ($path in $paths) {{
                if (Test-Path $path) {{
                    $shortcuts = Get-ChildItem -Path $path -Recurse -Filter *.lnk -ErrorAction SilentlyContinue
                    foreach ($shortcut in $shortcuts) {{
                        $name = [System.IO.Path]::GetFileNameWithoutExtension($shortcut.Name)
                        if ($name -like "*$appName*") {{
                            $shell = New-Object -ComObject WScript.Shell
                            $lnk = $shell.CreateShortcut($shortcut.FullName)
                            $target = $lnk.TargetPath
                            $args = $lnk.Arguments
                            if ($target -and (Test-Path $target)) {{
                                $found = @{{ Target = $target; Arguments = $args }}
                                break
                            }}
                        }}
                    }}
                    if ($found) {{ break }}
                }}
            }}
        }}
        if ($found) {{
            $process = Start-Process -FilePath $found.Target -ArgumentList $found.Arguments -PassThru -WindowStyle Normal
            if ($process) {{
                Write-Output "SUCCESS"
            }} else {{
                Write-Output "FAIL"
            }}
        }} else {{
            Write-Output "NOT_FOUND"
        }}
        '''
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15
            )
            stdout = result.stdout.strip()
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                return {"error": f"Ошибка PowerShell: {error_msg}"}

            if stdout == "SUCCESS":
                return {
                    "success": True,
                    "message": f"Приложение '{app_name}' успешно запущено"
                }
            elif stdout == "NOT_FOUND":
                return {
                    "error": f"Не удалось найти приложение '{app_name}'. Используйте action='list' для получения списка доступных имён."
                }
            else:
                return {"error": f"Неизвестный ответ от PowerShell: {stdout}"}
        except subprocess.TimeoutExpired:
            return {"error": "Превышено время ожидания при запуске приложения"}
        except Exception as e:
            return {"error": f"Неожиданная ошибка: {str(e)}"}