# tools/web_search/tool.py
# Инструмент для веб-поиска через DuckDuckGo и извлечения содержимого страниц

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS  # заменён устаревший duckduckgo_search
from tool_router import BaseTool

class Tool(BaseTool):
    """
    Инструмент выполняет два действия:
    1) Поиск в DuckDuckGo — возвращает список ссылок с заголовками и описаниями.
    2) Открытие указанной ссылки — возвращает текст страницы (без скриптов и стилей).
    """

    def get_manifest(self):
        return {
            "description": (
                "Выполняет поиск в DuckDuckGo по одному или нескольким запросам, "
                "возвращая ссылки с заголовками и кратким описанием. "
                "Также может открыть любую указанную ссылку и вернуть её текстовое содержимое "
                "(HTML очищается от скриптов, стилей и тегов, оставляя только читаемый текст)."
            ),
            "parameters": {
                "action": {
                    "type": "string",
                    "description": "Действие: 'search' или 'fetch'",
                    "enum": ["search", "fetch"]
                },
                "query": {
                    "type": "string",
                    "description": "Поисковый запрос (обязателен для action='search')"
                },
                "queries": {
                    "type": "array",
                    "description": "Список поисковых запросов (если указан, игнорируется query)",
                    "items": {"type": "string"}
                },
                "max_results": {
                    "type": "integer",
                    "description": "Максимальное количество результатов на запрос (по умолчанию 5)",
                    "default": 5
                },
                "url": {
                    "type": "string",
                    "description": "URL страницы для открытия (обязателен для action='fetch')"
                }
            }
        }

    def run(self, **kwargs):
        action = kwargs.get("action")
        if not action:
            return {"error": "Не указан параметр 'action' (должен быть 'search' или 'fetch')"}

        if action == "search":
            return self._search(kwargs)
        elif action == "fetch":
            return self._fetch(kwargs)
        else:
            return {"error": f"Недопустимое действие '{action}'. Используйте 'search' или 'fetch'."}

    # --------------------------------------------------------------------------
    # Поиск через DuckDuckGo
    # --------------------------------------------------------------------------
    def _search(self, params):
        queries = params.get("queries")
        if queries and isinstance(queries, list):
            pass
        else:
            query = params.get("query")
            if not query:
                return {"error": "Для поиска укажите 'query' или 'queries'"}
            queries = [query]

        max_results = params.get("max_results", 5)
        if not isinstance(max_results, int) or max_results <= 0:
            return {"error": "max_results должно быть положительным целым числом"}

        all_results = {}
        try:
            # Используем новый контекстный менеджер (если требуется) или прямой вызов
            ddgs = DDGS()
            for q in queries:
                results_list = []
                try:
                    # В новой библиотеке метод text() может быть другим – проверим
                    # Если возникает ошибка, пробуем ddgs.text(q, max_results=max_results)
                    for r in ddgs.text(q, max_results=max_results):
                        results_list.append({
                            "title": r.get("title"),
                            "href": r.get("href"),
                            "body": r.get("body")
                        })
                except Exception as e:
                    all_results[q] = {"error": f"Ошибка поиска: {str(e)}"}
                else:
                    all_results[q] = results_list
        except Exception as e:
            return {"error": f"Ошибка инициализации DuckDuckGo: {str(e)}"}

        return {
            "success": True,
            "result": all_results,
            "message": f"Выполнен поиск по {len(queries)} запросу(ам)"
        }

    # --------------------------------------------------------------------------
    # Открытие ссылки и извлечение чистого текста
    # --------------------------------------------------------------------------
    def _fetch(self, params):
        url = params.get("url")
        if not url:
            return {"error": "Для открытия страницы укажите 'url'"}

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            if resp.encoding is None:
                resp.encoding = resp.apparent_encoding

            soup = BeautifulSoup(resp.text, "html.parser")

            for element in soup(["script", "style", "meta", "link", "noscript"]):
                element.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = (line.strip() for line in text.splitlines())
            text = "\n".join(line for line in lines if line)

            max_len = 5000
            if len(text) > max_len:
                text = text[:max_len] + "\n...[обрезано по длине]"

            return {
                "success": True,
                "result": {
                    "url": url,
                    "content": text,
                    "content_length": len(text)
                },
                "message": f"Содержимое страницы получено ({len(text)} символов)"
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"Ошибка загрузки страницы: {str(e)}"}
        except Exception as e:
            return {"error": f"Неожиданная ошибка при обработке: {str(e)}"}