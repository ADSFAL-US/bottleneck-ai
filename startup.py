import os
import sys
import subprocess
import shutil
import psutil # pip install psutil

MAIN_SCRIPT = "main.py"

def check_dependencies():
    # Проверка Git
    if not shutil.which("git"):
        print("Ошибка: Git не найден. Пожалуйста, установите его.")
        sys.exit(1)
    
    # Проверка Python
    if not shutil.which("python"):
        print("Ошибка: Python не найден.")
        sys.exit(1)
        
    # Проверка LM Studio (просто ищем процесс)
    if not any("lmstudio" in p.name().lower() for p in psutil.process_iter()):
        print("Предупреждение: LM Studio не запущена. Модели могут не работать.")

def is_main_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        if proc.info['cmdline'] and MAIN_SCRIPT in proc.info['cmdline']:
            if proc.pid != os.getpid(): # Не считать сам этот скрипт
                return proc
    return None

def update_and_run():
    # 1. Проверка обновлений
    subprocess.run(["git", "fetch", "--all"], check=True)
    
    # Сравниваем локальный хеш с origin/main
    local = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/main"]).decode().strip()
    
    if local != remote:
        print("Найдено обновление. Обновляюсь...")
        # Принудительно забираем изменения
        subprocess.run(["git", "stash"])
        subprocess.run(["git", "pull", "origin", "main"])
        subprocess.run(["git", "stash", "pop"])
        
        # Убиваем старый процесс, если есть
        proc = is_main_running()
        if proc:
            print(f"Завершаю старую версию (PID {proc.pid})...")
            proc.terminate()
            proc.wait()
    else:
        # Обновлений нет, проверяем запущен ли уже
        if is_main_running():
            print("Ошибка: Программа уже запущена в другом экземпляре.")
            sys.exit(0)

    # 3. Запуск
    print("Запуск Bottleneck AI...")
    subprocess.Popen([sys.executable, MAIN_SCRIPT])

if __name__ == "__main__":
    check_dependencies()
    update_and_run()