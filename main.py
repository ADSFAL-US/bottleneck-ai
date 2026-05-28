import sys
from PyQt6.QtWidgets import QApplication
from config_manager import ConfigManager
from ui import AIAgentUI
from monitor import WinKeyMonitor
from tool_router import ToolRouter
from conversation_manager import ConversationManager # Убедись, что импорт есть

def main():
    app = QApplication(sys.argv)
    
    # 1. Сначала инициализируем менеджеры
    config_manager = ConfigManager()
    config_manager.load("config.json")
    conv_manager = ConversationManager()
    
    # 2. Инициализируем роутер
    # main.py
    router = ToolRouter()
    print(f"DEBUG: Найдено инструментов: {list(router.tools.keys())}")
    print(f"DEBUG: Промпт расширенный: {router.get_system_prompt_extension()}")
    
    # 3. Формируем промпт
    sys_prompt = config_manager.get("lm_studio.system_prompt") + router.get_system_prompt_extension()
    
    # 4. Передаем ВСЕ аргументы в UI
    ui = AIAgentUI(
        conversation_manager=conv_manager, 
        config_manager=config_manager, 
        system_prompt=sys_prompt, 
        router=router
    )
    
    monitor = WinKeyMonitor(
        hold_seconds=config_manager.get("hotkey.win_hold_seconds", 3.0),
        check_interval=config_manager.get("hotkey.check_interval", 0.1)
    )
    
    monitor.trigger_window.connect(ui.show_animated)
    monitor.start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()