# tools/process_manager/tool.py
"""
Инструмент управления процессами: получение списка процессов с фильтрацией и сортировкой,
завершение процессов, поиск по имени и пути исполняемого файла.
Использует библиотеку psutil для кроссплатформенной работы.
"""

import psutil
from tool_router import BaseTool

class Tool(BaseTool):
    """
    Инструмент для мониторинга и управления системными процессами.
    Поддерживает три действия:
    - list: получить список процессов (фильтрация по имени, сортировка по CPU/памяти/сети)
    - kill: завершить процесс по PID
    - search: найти процессы по ключевому слову в имени или пути
    """

    def get_manifest(self):
        """
        Манифест инструмента.
        Определяет единственный параметр 'action' и набор дополнительных параметров в зависимости от действия.
        """
        return {
            "description": (
                "Управление процессами операционной системы. "
                "Позволяет получить список работающих процессов с возможностью фильтрации по имени "
                "и сортировки по использованию CPU, памяти или количеству сетевых соединений. "
                "Также поддерживает завершение процесса по PID и поиск процессов по ключевым словам "
                "в имени или пути исполняемого файла."
            ),
            "parameters": {
                "action": {
                    "type": "string",
                    "description": "Действие: 'list' (список процессов), 'kill' (завершить процесс), 'search' (поиск процессов)",
                    "enum": ["list", "kill", "search"],
                    "required": True
                },
                # Общие параметры для нескольких действий
                "filter": {
                    "type": "string",
                    "description": "Строка фильтрации для 'list' и 'search' – искать только процессы, содержащие эту подстроку в имени"
                },
                "sort_by": {
                    "type": "string",
                    "description": "Поле сортировки для 'list': 'cpu' (процессор), 'memory' (память), 'network' (сетевые соединения)",
                    "enum": ["cpu", "memory", "network"]
                },
                "reverse": {
                    "type": "boolean",
                    "description": "Обратный порядок сортировки (по убыванию) для 'list'",
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Максимальное количество процессов в результате для 'list'",
                    "minimum": 1
                },
                # Параметры для kill
                "pid": {
                    "type": "integer",
                    "description": "Идентификатор процесса (PID) для действия 'kill'",
                    "minimum": 1
                },
                # Параметры для search
                "path": {
                    "type": "string",
                    "description": "Путь к исполняемому файлу (полный или часть) для поиска в действии 'search'"
                }
            }
        }

    def run(self, **kwargs):
        """
        Выполняет запрошенное действие.
        """
        action = kwargs.get("action")
        if not action:
            return {"error": "Не указано действие 'action' (должно быть 'list', 'kill' или 'search')"}

        try:
            if action == "list":
                return self._list_processes(
                    filter_str=kwargs.get("filter"),
                    sort_by=kwargs.get("sort_by"),
                    reverse=kwargs.get("reverse", True),
                    limit=kwargs.get("limit")
                )
            elif action == "kill":
                return self._kill_process(kwargs.get("pid"))
            elif action == "search":
                return self._search_processes(
                    keyword=kwargs.get("filter"),  # для поиска используем filter как ключевое слово
                    path_pattern=kwargs.get("path")
                )
            else:
                return {"error": f"Неизвестное действие: {action}"}
        except Exception as e:
            return {"error": f"Ошибка при выполнении '{action}': {str(e)}"}

    # ----------------------------------------------------------------------
    # Вспомогательные методы
    # ----------------------------------------------------------------------

    def _list_processes(self, filter_str=None, sort_by=None, reverse=True, limit=None):
        """
        Собирает информацию о процессах, фильтрует, сортирует и возвращает список.
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'exe']):
            try:
                # Получаем основные атрибуты
                pinfo = proc.info
                pid = pinfo['pid']
                name = pinfo['name'] or ''
                cpu = pinfo['cpu_percent'] or 0.0
                memory = pinfo['memory_percent'] or 0.0
                exe_path = pinfo['exe'] or ''

                # Фильтрация по имени (если задана)
                if filter_str:
                    if filter_str.lower() not in name.lower():
                        continue

                # Количество сетевых соединений (требуется дополнительный вызов)
                try:
                    connections = len(proc.connections())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    connections = 0

                processes.append({
                    "pid": pid,
                    "name": name,
                    "cpu_percent": round(cpu, 2),
                    "memory_percent": round(memory, 2),
                    "connections": connections,
                    "exe_path": exe_path
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Сортировка
        if sort_by:
            if sort_by == "cpu":
                processes.sort(key=lambda p: p["cpu_percent"], reverse=reverse)
            elif sort_by == "memory":
                processes.sort(key=lambda p: p["memory_percent"], reverse=reverse)
            elif sort_by == "network":
                processes.sort(key=lambda p: p["connections"], reverse=reverse)
            # Если sort_by указан некорректно, сортируем по умолчанию (по PID)
            else:
                processes.sort(key=lambda p: p["pid"])
        else:
            processes.sort(key=lambda p: p["pid"])

        # Ограничение количества записей
        if limit is not None and limit > 0:
            processes = processes[:limit]

        return {
            "success": True,
            "result": processes,
            "count": len(processes),
            "message": f"Получено {len(processes)} процессов" + (f" (фильтр: '{filter_str}')" if filter_str else "")
        }

    def _kill_process(self, pid):
        """
        Завершает процесс с указанным PID.
        """
        if pid is None:
            return {"error": "Для действия 'kill' требуется параметр 'pid'"}

        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()  # вежливое завершение
            # Ждём немного (опционально)
            gone, alive = psutil.wait_procs([proc], timeout=3)
            if proc in alive:
                # если не завершился, принудительно убиваем
                proc.kill()
                return {
                    "success": True,
                    "message": f"Процесс {proc_name} (PID {pid}) был принудительно завершён после таймаута"
                }
            else:
                return {
                    "success": True,
                    "message": f"Процесс {proc_name} (PID {pid}) успешно завершён"
                }
        except psutil.NoSuchProcess:
            return {"error": f"Процесс с PID {pid} не найден"}
        except psutil.AccessDenied:
            return {"error": f"Недостаточно прав для завершения процесса {pid}"}
        except Exception as e:
            return {"error": f"Ошибка при завершении процесса {pid}: {str(e)}"}

    def _search_processes(self, keyword=None, path_pattern=None):
        """
        Ищет процессы по ключевому слову в имени или по шаблону пути исполняемого файла.
        Возвращает список подходящих процессов.
        """
        if not keyword and not path_pattern:
            return {"error": "Для поиска укажите хотя бы один из параметров: 'filter' (имя) или 'path' (путь)"}

        results = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                pinfo = proc.info
                pid = pinfo['pid']
                name = pinfo['name'] or ''
                exe_path = pinfo['exe'] or ''

                match = False
                if keyword and keyword.lower() in name.lower():
                    match = True
                if path_pattern and path_pattern.lower() in exe_path.lower():
                    match = True

                if match:
                    results.append({
                        "pid": pid,
                        "name": name,
                        "exe_path": exe_path
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "success": True,
            "result": results,
            "count": len(results),
            "message": f"Найдено {len(results)} процессов по запросу" + (f" (имя: '{keyword}')" if keyword else "") + (f" (путь: '{path_pattern}')" if path_pattern else "")
        }