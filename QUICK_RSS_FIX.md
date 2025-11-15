# Быстрое исправление RSS для Apple Podcasts

## Проблема
```
we cannot find a podcast feed with this url
```

## Причина
Отсутствуют обязательные теги: `<language>`, `<itunes:image>`, неправильные namespace префиксы.

## Быстрое решение (3 шага)

### 1. Установить изображение подкаста

```bash
# На Railway через CLI
railway variables set PODCAST_IMAGE=https://2vlad.github.io/vlad-podcast/podcast-cover.jpg
```

**Или через веб-интерфейс Railway:**
- Settings → Variables → Add Variable
- Name: `PODCAST_IMAGE`
- Value: URL вашего изображения (1400x1400px минимум, JPG/PNG)

### 2. Регенерировать RSS фид

```bash
# Локально с Railway CLI
cd /Users/admin/Dev/youtube-podcast
railway run python fix_rss_namespace.py

# Или деплой кода и запуск на Railway
git push
railway run bash
python fix_rss_namespace.py
exit
```

### 3. Проверить и переподписаться

```bash
# Проверить RSS
curl -s https://vlad-podcast-production.up.railway.app/rss.xml | grep -E "language|itunes:image"
```

Должно показать:
```xml
<language>ru</language>
<itunes:image href="https://..."/>
```

**В подкаст-приложении:**
1. **Удалите** старую подписку
2. **Добавьте** заново: `https://vlad-podcast-production.up.railway.app/rss.xml`

## Детали

См. полную документацию: [RSS_FIX_GUIDE.md](./RSS_FIX_GUIDE.md)

## Проверка

Валидатор: https://castfeedvalidator.com/
URL: `https://vlad-podcast-production.up.railway.app/rss.xml`

---

**Важно:** После изменения RSS **обязательно** удалите старую подписку и добавьте заново. Подкаст-приложения кэшируют неудачные попытки.
