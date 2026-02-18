# Инструкция по сборке PayrollSystem

## Требования

- Python 3.12+
- PyInstaller
- Inno Setup 6 (для создания инсталлятора)

## Установка зависимостей

```bash
pip install -r requirements.txt
pip install pyinstaller
```

## Сборка EXE файла

### Метод 1: Использование spec-файла (рекомендуется)

```bash
pyinstaller PayrollSystem.spec --clean --noconfirm
```

### Метод 2: Прямая команда

```bash
pyinstaller --onefile --windowed --icon=icon.ico --name=PayrollSystem ^
  --add-data "icon.ico;." ^
  --add-data "fonts/DejaVuSans.ttf;fonts" ^
  --add-data "templates/*.json;templates" ^
  --hidden-import babel.numbers ^
  app.py
```

После успешной сборки EXE файл будет находиться в папке `dist/PayrollSystem.exe`.

## Создание инсталлятора

### Требования

Установите [Inno Setup 6](https://jrsoftware.org/isdl.php)

### Сборка инсталлятора

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" PayrollSystem.iss
```

Инсталлятор будет создан в папке `output/PayrollSystem_v1.7.0_Setup.exe`.

## Структура файлов после сборки

```
PayrollSystem/
├── dist/
│   └── PayrollSystem.exe          # Исполняемый файл (~39 MB)
├── output/
│   └── PayrollSystem_v1.7.0_Setup.exe  # Инсталлятор (~40 MB)
├── build/                         # Временные файлы сборки
└── ...
```

## Тестирование

1. Запустите `dist/PayrollSystem.exe` для проверки работоспособности
2. Установите приложение через инсталлятор для проверки процесса установки
3. Проверьте создание ярлыков на рабочем столе и в меню Пуск

## Распространение

Для распространения используйте файл `output/PayrollSystem_v1.7.0_Setup.exe`.

Инсталлятор включает:
- Автоматическую установку в `%LOCALAPPDATA%\Programs\PayrollSystem`
- Создание ярлыков в меню Пуск
- Опциональный ярлык на рабочем столе
- Опциональный запуск при старте Windows
- Полное удаление через панель управления

## Примечания

- База данных создается автоматически в `%LOCALAPPDATA%\PayrollSystem\payroll.db`
- При удалении приложения база данных также удаляется
- Для обновления версии измените `APP_VERSION` в `core/version.py` и `AppVersion` в `PayrollSystem.iss`
