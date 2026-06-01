from datetime import datetime
from tool_router import BaseTool

class Tool(BaseTool):
    def get_manifest(self):
        return {"description": "Возвращает текущее время.", "parameters": {}}
    
    def run(self, **kwargs):
        return {"time": datetime.now().strftime("%H:%M:%S")}