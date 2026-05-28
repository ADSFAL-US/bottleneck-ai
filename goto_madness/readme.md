code example

from holy_madness import cursed_zone

# Заглушки, чтобы Python не ругался на синтаксис при чтении файла
class label: pass
class goto: pass

def crazy_loop():
    x = 0
    
    label.nachyi  # Наша метка
    
    x += 1
    print(f"Плюсанули x, теперь он: {x}")
    
    if x < 5:
        print("Мало! Иди нахер обратно наверх!")
        goto.nachyi  # Тот самый прыжок
        
    print("Ну всё, теперь можно и выйти.")

# Применяем магию вручную и запускаем!
crazy_loop = cursed_zone(crazy_loop)
crazy_loop()