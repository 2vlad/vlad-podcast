# Руководство по отладке загрузки больших MP4 файлов

## Обзор

Это руководство поможет диагностировать проблемы с загрузкой больших MP4 файлов и их преобразованием в эпизоды подкаста.

## Добавленное логирование

### В `web.py`

Добавлено подробное логирование в следующих местах:

1. **`upload_file()` endpoint** - точка входа для загрузки файлов:
   - Валидация файла
   - Сохранение во временную директорию
   - Размер загруженного файла
   - Создание job и запуск обработки

2. **`process_upload_job()`** - фоновая обработка загруженного файла:
   - Проверка существования файла и его размера
   - Генерация хеша файла
   - Конвертация MP4 в аудио (с FFmpeg)
   - Извлечение метаданных
   - Создание эпизода в RSS
   - Сохранение RSS фида
   - Публикация на GitHub (если настроено)

### В `utils/rss_manager.py`

Добавлено логирование в:

1. **`add_episode()`** - добавление эпизода в RSS:
   - Информация об эпизоде (GUID, title, URL, размер)
   - Каждый шаг добавления полей
   - Статус успешности/ошибки

2. **`save_feed()`** - сохранение RSS файла:
   - Путь к RSS файлу
   - Количество эпизодов
   - Размер сохраненного файла
   - Проверка создания файла

## Как тестировать локально

### 1. Запустить веб-сервер локально

```bash
# Убедитесь, что .env настроен
python web.py
```

Сервер запустится на `http://localhost:5001`

### 2. Использовать тестовый скрипт

```bash
# Загрузить MP4 файл
python test_upload.py /path/to/your/video.mp4

# Или указать другой URL сервера
python test_upload.py video.mp4 http://localhost:5001
```

### 3. Отслеживать логи

Логи будут выводиться в:
- **Консоль** (stdout) - где запущен `web.py`
- **Файл** `logs/web.log` - с ротацией (макс 10MB, 5 файлов)

## Включение DEBUG логирования

Для более подробных логов измените уровень логирования:

### Вариант 1: Через код

В `web.py` или в начале скрипта:

```python
import logging
from utils.logger import setup_logger

# Установить DEBUG уровень для всех логгеров
logging.basicConfig(level=logging.DEBUG)

# Или только для определенных модулей
logger = setup_logger("web", level=logging.DEBUG)
```

### Вариант 2: Через переменную окружения

```bash
export LOG_LEVEL=DEBUG
python web.py
```

### Вариант 3: Использовать скрипт

```bash
# Запустить с DEBUG логированием
python -u web.py 2>&1 | tee debug_output.log
```

## Что смотреть в логах

### Успешная загрузка

```
📤 New file upload request received
Upload filename: video.mp4
Upload metadata - Title: My Video, Description: Test
Temp directory: /path/to/podcast/temp
Saving file to: /path/to/podcast/temp/video.mp4
File saved successfully - Size: 123.45 MB (129499136 bytes)
Created job 1 for file: video.mp4
Starting background processing thread for job 1
Background thread started for job 1

[Job 1] Starting upload processing for: video.mp4
[Job 1] File size: 123.45 MB (129499136 bytes)
[Job 1] File path: /path/to/podcast/temp/video.mp4
[Job 1] Settings loaded - Media dir: /path/to/podcast/media, Audio format: m4a
[Job 1] Directories verified
[Job 1] Generating file hash...
[Job 1] Generated file hash: abc123def45
[Job 1] File extension: .mp4, Target format: m4a
[Job 1] MP4 file detected, starting conversion to m4a
[Job 1] Output file will be: /path/to/podcast/media/abc123def45.m4a
[Job 1] FFmpeg command: ffmpeg -loglevel info -i /path/to/temp/video.mp4 -vn -acodec aac -q:a 2 /path/to/media/abc123def45.m4a
[Job 1] Starting FFmpeg conversion...
[Job 1] FFmpeg conversion successful
[Job 1] Converted file size: 12.34 MB
[Job 1] Removed original MP4 file
[Job 1] Extracting metadata from audio file
[Job 1] Final audio file size: 12.34 MB (12943872 bytes)
[Job 1] Episode title: My Video
[Job 1] Starting RSS feed update
[Job 1] Creating RSS manager
[Job 1] Loading existing RSS feed from: /path/to/podcast/rss.xml
[Job 1] Existing feed loaded successfully
[Job 1] Found 5 existing episodes in feed
[Job 1] Audio URL: https://example.com/media/abc123def45.m4a
[Job 1] MIME type: audio/mp4
[Job 1] Episode GUID: abc123def45
[Job 1] Creating episode data structure
[Job 1] Adding episode to RSS feed
Adding episode to RSS feed - GUID: abc123def45
  Title: My Video
  Audio URL: https://example.com/media/abc123def45.m4a
  File size: 12.34 MB
  MIME type: audio/mp4
  Duration: None
✅ Successfully added episode abc123def45 to feed
[Job 1] Episode added to feed successfully
[Job 1] Saving RSS feed to: /path/to/podcast/rss.xml
Saving RSS feed to: /path/to/podcast/rss.xml
Feed contains 6 episodes
✅ RSS feed saved successfully - Size: 8.56 KB (8765 bytes)
[Job 1] RSS feed saved successfully
[Job 1] ✅ Successfully processed uploaded file: video.mp4
[Job 1] Episode ID: abc123def45
[Job 1] Episode title: My Video
[Job 1] Audio file: /path/to/podcast/media/abc123def45.m4a
[Job 1] File size: 12.34 MB
[Job 1] Job completed successfully
```

### Признаки проблем

#### 1. Файл не загрузился
```
❌ File not found: /path/to/temp/video.mp4
```
→ Проблема с сохранением загружаемого файла

#### 2. FFmpeg конвертация не удалась
```
[Job 1] FFmpeg conversion failed with code 1
[Job 1] FFmpeg stderr: [ошибка FFmpeg]
[Job 1] Falling back to using original MP4 file
```
→ Проверить установку FFmpeg или формат файла

#### 3. Не создан выходной файл
```
[Job 1] Output file was not created: /path/to/output.m4a
```
→ Проблема с правами доступа или нехватка места на диске

#### 4. Не удалось добавить в RSS
```
❌ Failed to add episode abc123 to feed: [ошибка]
```
→ Проблема с RSS менеджером или данными эпизода

#### 5. Не удалось сохранить RSS
```
❌ Failed to save RSS feed: [ошибка]
❌ RSS file was not created: /path/to/rss.xml
```
→ Проблема с правами доступа или с feedgen

## Проверка системных требований

### FFmpeg

```bash
# Проверить установку FFmpeg
ffmpeg -version

# Тест конвертации вручную
ffmpeg -i video.mp4 -vn -acodec aac -q:a 2 output.m4a
```

### Свободное место

```bash
# Проверить свободное место
df -h

# Размер директорий проекта
du -sh podcast/media
du -sh podcast/temp
```

### Права доступа

```bash
# Проверить права доступа
ls -la podcast/
ls -la podcast/media/
ls -la podcast/temp/

# Если нужно, исправить права
chmod -R 755 podcast/
```

## Частые проблемы и решения

### 1. Большой файл не загружается

**Проблема**: Upload прерывается или таймаут

**Решение**:
- Увеличить `MAX_CONTENT_LENGTH` в `web.py` (сейчас 500MB)
- Увеличить таймаут в Nginx/прокси (если используется)
- Проверить лимиты системы:
  ```bash
  ulimit -a  # Проверить лимиты
  ulimit -n 4096  # Увеличить лимит файловых дескрипторов
  ```

### 2. FFmpeg работает слишком долго

**Проблема**: Конвертация большого файла занимает много времени

**Решение**:
- Это нормально для больших файлов
- Следить за прогрессом в логах FFmpeg
- При необходимости оптимизировать параметры FFmpeg

### 3. Эпизод не появляется в RSS

**Проблема**: Обработка завершилась успешно, но эпизода нет в фиде

**Решение**:
- Проверить содержимое `podcast/rss.xml`
- Проверить `existing_guids` - возможно эпизод уже есть
- Проверить `max_items` в настройках

### 4. Ошибки памяти

**Проблема**: Out of memory при обработке больших файлов

**Решение**:
- FFmpeg обычно не использует много памяти
- Проверить использование памяти: `htop` или `top`
- Убедиться, что достаточно swap-пространства

## Сбор диагностической информации

Для отчета о баге соберите:

1. **Логи**:
   ```bash
   tail -n 500 logs/web.log > debug_logs.txt
   ```

2. **Информация о системе**:
   ```bash
   python --version
   ffmpeg -version
   df -h
   free -h
   ```

3. **Информация о файле**:
   ```bash
   ls -lh video.mp4
   ffprobe video.mp4
   ```

4. **Конфигурация**:
   ```bash
   cat .env | grep -v "PASSWORD\|SECRET\|KEY"
   ```

## Дополнительные инструменты

### Мониторинг в реальном времени

```bash
# Следить за логами в реальном времени
tail -f logs/web.log | grep "Job"

# Фильтровать только ошибки
tail -f logs/web.log | grep "ERROR\|❌"

# Следить за использованием ресурсов
watch -n 1 'ps aux | grep -E "python|ffmpeg"'
```

### Проверка RSS файла

```bash
# Валидировать RSS
xmllint --noout podcast/rss.xml && echo "✅ Valid XML" || echo "❌ Invalid XML"

# Посмотреть количество эпизодов
grep -c "<item>" podcast/rss.xml

# Посмотреть GUIDs эпизодов
grep "<guid>" podcast/rss.xml
```

## Контакты и поддержка

При обнаружении багов создавайте issue с:
- Описанием проблемы
- Размером и форматом файла
- Логами (см. раздел "Сбор диагностической информации")
- Ожидаемым и фактическим поведением
