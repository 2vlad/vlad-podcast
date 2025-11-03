# YouTube to Podcast Converter - Features

## ✨ Реализованные функции

### 1. 🎯 Базовая функциональность
- ✅ Скачивание аудио из YouTube видео (yt-dlp)
- ✅ Конвертация в m4a/mp3 формат (FFmpeg)
- ✅ Генерация RSS фида (iTunes совместимый)
- ✅ Извлечение метаданных (название, описание, длительность)
- ✅ Сохранение локально в структурированных папках

### 2. 🌐 Веб-интерфейс
- ✅ Apple-style минималистичный дизайн (черно-белый)
- ✅ Responsive layout (работает на мобильных)
- ✅ Real-time статус обработки
- ✅ **Прогресс-бар загрузки** 📊
  - Процент завершения (0-100%)
  - Скорость загрузки (KB/s, MB/s)
  - Оставшееся время (ETA)
  - Плавная анимация
- ✅ Отображение результата (название, длительность, размер файла)
- ✅ Обработка ошибок с понятными сообщениями

### 3. 🚀 Backend
- ✅ Flask REST API
- ✅ Асинхронная обработка (threading)
- ✅ Job tracking system
- ✅ Progress streaming через polling
- ✅ Error handling и logging
- ✅ Конфигурация через .env файл

### 4. 📤 Автоматический деплой на Mave.digital
- ✅ Модульная система загрузки
- ✅ Поддержка **5 методов загрузки**:
  1. **Manual** (по умолчанию) - сохранение локально
  2. **WebDAV** - для облачных хостингов
  3. **FTP** - классический протокол
  4. **SFTP** - безопасный FTP
  5. **rsync** - синхронизация файлов
- ✅ Автоматическая загрузка аудио файлов
- ✅ Автоматическая загрузка RSS фида
- ✅ Connection testing перед загрузкой
- ✅ Fallback на локальное сохранение при ошибке

### 5. 🛡️ Обработка ошибок
- ✅ **YouTube 403 Forbidden** - обход через multiple player clients
- ✅ **Datetime timezone** - корректная работа с UTC
- ✅ **Thumbnail format** - graceful handling WebP формата
- ✅ **Duplicate detection** - проверка GUID перед добавлением
- ✅ Подробное логирование всех операций

### 6. 📊 RSS Feed
- ✅ iTunes podcast теги (author, category, duration, explicit)
- ✅ Episode metadata (title, description, pubDate, enclosure)
- ✅ Atom self-link для совместимости
- ✅ Корректные MIME types (audio/mp4, audio/mpeg)
- ✅ Валидный XML (проверен)
- ✅ Ограничение количества эпизодов (configurable)

### 7. ⚙️ Конфигурация
- ✅ `.env` файл для настроек
- ✅ Dataclass-based configuration
- ✅ Validation при старте
- ✅ Понятные error messages
- ✅ Настройки для:
  - Podcast metadata (title, description, author)
  - Audio format (m4a/mp3)
  - Feed limits
  - Upload method и credentials

## 📸 Скриншоты

### Прогресс-бар в действии
```
Downloading: 45.3% (8.9 MB/s, ETA: 3s)
[████████████████▓▓▓▓▓▓▓▓] 45%
```

### Результат обработки
```
✓ Rick Astley - Never Gonna Give You Up
  Длительность: 03:33
  dQw4w9WgXcQ.m4a
```

## 🎯 Технологии

**Backend:**
- Python 3.9+
- Flask 3.0 (веб-сервер)
- yt-dlp (YouTube downloader)
- feedgen (RSS generation)
- FFmpeg (audio conversion)

**Frontend:**
- Vanilla JavaScript (ES6+)
- CSS3 (Apple-style дизайн)
- No frameworks (максимальная производительность)

**Upload:**
- webdavclient3 (WebDAV support)
- paramiko (SFTP support)
- ftplib (встроенная FTP поддержка)
- rsync (через subprocess)

## 📁 Структура проекта

```
youtube-podcast/
├── web.py                    # Flask веб-сервер
├── yt2pod.py                # CLI версия
├── config.py                # Конфигурация
├── requirements.txt         # Python зависимости
├── .env                     # Настройки (не в git)
├── .env.example            # Пример настроек
│
├── utils/
│   ├── downloader.py       # YouTube загрузка + progress tracking
│   ├── rss_manager.py      # RSS генерация
│   ├── url_processor.py    # URL парсинг
│   ├── logger.py           # Логирование
│   └── mave_uploader.py    # 🆕 Автоматическая загрузка на Mave
│
├── templates/
│   └── index.html          # Веб-интерфейс
│
├── static/
│   ├── app.js              # Frontend логика + progress bar
│   └── style.css           # Apple-style дизайн
│
└── podcast/
    ├── rss.xml             # RSS фид
    └── media/              # Аудио файлы
        ├── dQw4w9WgXcQ.m4a
        └── X-ot9682-1w.m4a
```

## 🚀 Quick Start

### 1. Установка
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Конфигурация
```bash
cp .env.example .env
# Отредактируй .env:
# - SITE_URL (твой Mave.digital URL)
# - MEDIA_BASE_URL
# - MAVE_UPLOAD_METHOD (manual/webdav/ftp/sftp)
```

### 3. Запуск
```bash
# Веб-интерфейс
python web.py
# Откройте http://localhost:5001

# CLI версия
python yt2pod.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 🔧 Настройка автоматической загрузки

### Вариант 1: Manual (по умолчанию)
```bash
MAVE_UPLOAD_METHOD="manual"
```
Файлы сохраняются локально, загрузка вручную.

### Вариант 2: WebDAV
```bash
MAVE_UPLOAD_METHOD="webdav"
MAVE_WEBDAV_URL="https://cloud.mave.digital/67282/webdav"
MAVE_USERNAME="your_username"
MAVE_PASSWORD="your_password"
```

### Вариант 3: FTP/SFTP
```bash
MAVE_UPLOAD_METHOD="sftp"  # или "ftp"
MAVE_FTP_HOST="ftp.mave.digital"
MAVE_USERNAME="your_username"
MAVE_PASSWORD="your_password"
MAVE_FTP_PORT="22"  # 21 для FTP, 22 для SFTP
```

### Вариант 4: rsync
```bash
MAVE_UPLOAD_METHOD="rsync"
MAVE_FTP_HOST="your-server.com"
MAVE_USERNAME="your_username"
# Требует SSH key setup
```

## 📊 API Endpoints

```
GET  /                      # Веб-интерфейс
GET  /api/config            # Получить конфигурацию
POST /api/process           # Начать обработку URL
GET  /api/status/<job_id>   # Проверить статус задачи
```

### Пример API запроса
```bash
# Начать обработку
curl -X POST http://localhost:5001/api/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Ответ:
{
  "job_id": 1,
  "status": "pending"
}

# Проверить статус
curl http://localhost:5001/api/status/1

# Ответ с прогрессом:
{
  "id": 1,
  "status": "processing",
  "message": "Downloading: 45.3% (8.9 MB/s, ETA: 3s)",
  "progress": {
    "status": "downloading",
    "percent": 45.3,
    "speed": "8.9 MB/s",
    "eta": "3s"
  }
}
```

## 🎓 Lessons Learned

### Проблемы и решения
1. **YouTube 403** → user-agent + multiple player clients
2. **Timezone errors** → always use UTC with timezone info
3. **WebP thumbnails** → try-except with graceful fallback
4. **Progress tracking** → yt-dlp progress_hooks
5. **Stale snapshots** → always take fresh snapshot before UI interaction

### Best practices
- ✅ Use dataclasses для configuration
- ✅ Separate concerns (downloader, RSS, uploader)
- ✅ Progress callbacks для user feedback
- ✅ Graceful error handling
- ✅ Comprehensive logging
- ✅ Environment-based configuration

## 🔮 Будущие улучшения

### v2.0 Features
- [ ] Batch processing (несколько URL одновременно)
- [ ] Playlist support
- [ ] Scheduled downloads (cron-like)
- [ ] Webhook notifications
- [ ] Dark mode toggle
- [ ] Audio normalization
- [ ] ID3 tags embedding
- [ ] Chapter markers
- [ ] Multi-language support
- [ ] Docker container
- [ ] Desktop app (Electron)

### Интеграции
- [ ] Spotify podcasts
- [ ] SoundCloud
- [ ] Apple Podcasts API
- [ ] Telegram bot
- [ ] Discord bot

## 📝 License

MIT License - используй как хочешь!

## 🤝 Contributing

Pull requests welcome! 

## 💬 Support

Вопросы? Открой issue в GitHub или свяжись с автором.

---

**Сделано с ❤️ для любителей подкастов**
