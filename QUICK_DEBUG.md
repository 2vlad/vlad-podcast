# Быстрая отладка загрузки MP4 файлов

## Быстрый старт

### 1. Запустить сервер с DEBUG логированием

```bash
./run_debug.sh
```

Или вручную:
```bash
export LOG_LEVEL=DEBUG
python web.py
```

### 2. Загрузить тестовый файл

В отдельном терминале:

```bash
# Простой способ
./test_upload.py /path/to/video.mp4

# Или с Python
python test_upload.py /path/to/video.mp4
```

### 3. Отслеживать логи

Логи автоматически выводятся в консоль и сохраняются в:
- `logs/web.log` - основной лог файл
- `logs/debug_YYYYMMDD_HHMMSS.log` - лог сессии (при использовании run_debug.sh)

## Что вы увидите в логах

### ✅ Успешная загрузка и обработка

```
================================================================================
📤 New file upload request received
Upload filename: video.mp4
File saved successfully - Size: 123.45 MB (129499136 bytes)
Created job 1 for file: video.mp4

[Job 1] Starting upload processing for: video.mp4
[Job 1] File size: 123.45 MB (129499136 bytes)
[Job 1] MP4 file detected, starting conversion to m4a
[Job 1] FFmpeg conversion successful
[Job 1] Converted file size: 12.34 MB
[Job 1] Adding episode to RSS feed
✅ Successfully added episode abc123 to feed
✅ RSS feed saved successfully - Size: 8.56 KB
[Job 1] ✅ Successfully processed uploaded file: video.mp4
```

### ❌ Проблема с конвертацией

```
[Job 1] FFmpeg conversion failed with code 1
[Job 1] FFmpeg stderr: [детали ошибки]
[Job 1] Falling back to using original MP4 file
```

### ❌ Проблема с RSS

```
[Job 1] Failed to add episode to feed: [ошибка]
```

## Команды для диагностики

### Следить за логами в реальном времени

```bash
# Все логи
tail -f logs/web.log

# Только для конкретного job
tail -f logs/web.log | grep "Job 1"

# Только ошибки
tail -f logs/web.log | grep "ERROR\|❌"

# Только успехи
tail -f logs/web.log | grep "✅"
```

### Проверить обработанные файлы

```bash
# Аудио файлы
ls -lh podcast/media/

# RSS фид
cat podcast/rss.xml | grep "<item>" -A 10

# Количество эпизодов
grep -c "<item>" podcast/rss.xml
```

### Проверить FFmpeg

```bash
# Версия FFmpeg
ffmpeg -version

# Тест конвертации
ffmpeg -i test.mp4 -vn -acodec aac -q:a 2 test_output.m4a
```

## Уровни логирования

Доступные уровни (через `LOG_LEVEL`):

- `DEBUG` - максимально подробные логи (рекомендуется для отладки)
- `INFO` - обычный режим (по умолчанию)
- `WARNING` - только предупреждения и ошибки
- `ERROR` - только ошибки
- `CRITICAL` - только критические ошибки

Пример:
```bash
export LOG_LEVEL=DEBUG
python web.py
```

## Тестирование с curl

Если предпочитаете curl вместо Python скрипта:

```bash
curl -X POST http://localhost:5001/api/upload \
  -F "file=@/path/to/video.mp4" \
  -F "title=Test Video" \
  -F "description=Test upload"
```

Затем проверить статус (замените JOB_ID):
```bash
curl http://localhost:5001/api/status/1
```

## Сохранение логов для отчета

```bash
# Скопировать последние 500 строк логов
tail -n 500 logs/web.log > bug_report_logs.txt

# Или весь лог файл
cp logs/web.log bug_report_logs.txt

# Или конкретную debug сессию
cp logs/debug_20231116_143022.log bug_report_logs.txt
```

## Частые проблемы

### 1. Сервер не запускается

```bash
# Проверить порт 5001
lsof -i :5001

# Убить процесс на порту
kill -9 $(lsof -t -i:5001)
```

### 2. Файл слишком большой

Увеличить лимит в `web.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1GB
```

### 3. FFmpeg не найден

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Проверить установку
which ffmpeg
```

### 4. Нет прав на запись

```bash
# Дать права на директории
chmod -R 755 podcast/
mkdir -p podcast/temp podcast/media
```

## Полная документация

Для подробной информации смотрите: [UPLOAD_DEBUG_GUIDE.md](UPLOAD_DEBUG_GUIDE.md)
