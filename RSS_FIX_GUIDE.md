# RSS Feed Fix Guide

## Проблема

RSS фид на Railway не распознается подкаст-приложениями (Apple Podcasts, Overcast, Pocket Casts) из-за:

1. ❌ Отсутствует обязательный тег `<language>` 
2. ❌ Отсутствует обязательный тег `<itunes:image>` (обложка подкаста)
3. ❌ Неправильные namespace префиксы (`ns0`, `ns1` вместо `atom`, `itunes`)
4. ❌ Возможно отсутствуют другие обязательные iTunes теги

## Решение

### Шаг 1: Добавить изображение подкаста

Подкасту нужна обложка (минимум 1400x1400px, максимум 3000x3000px).

**Вариант А: Загрузить изображение на GitHub**

1. Создайте квадратное изображение 1400x1400px или больше
2. Сохраните как `podcast-cover.jpg` или `podcast-cover.png`
3. Загрузите в репозиторий GitHub:
   ```bash
   git add docs/podcast-cover.jpg
   git commit -m "Add podcast cover image"
   git push
   ```
4. URL изображения будет: `https://2vlad.github.io/vlad-podcast/podcast-cover.jpg`

**Вариант Б: Использовать внешний URL**

Загрузите изображение на любой хостинг изображений (Imgur, Cloudinary, etc.) и получите прямую ссылку.

### Шаг 2: Установить переменную окружения на Railway

Установите переменную `PODCAST_IMAGE` с URL изображения:

```bash
# Через Railway CLI
railway variables set PODCAST_IMAGE=https://2vlad.github.io/vlad-podcast/podcast-cover.jpg

# Или через веб-интерфейс Railway:
# Settings → Variables → Add Variable
# Name: PODCAST_IMAGE
# Value: https://2vlad.github.io/vlad-podcast/podcast-cover.jpg
```

### Шаг 3: Регенерировать RSS фид

На Railway, выполните скрипт исправления:

```bash
# Через Railway CLI (локально)
railway run python fix_rss_namespace.py

# Или через SSH на Railway
railway run bash
python fix_rss_namespace.py
exit
```

Скрипт:
- ✅ Создаст бэкап существующего RSS (`podcast/rss.xml.backup`)
- ✅ Прочитает все существующие эпизоды
- ✅ Создаст новый RSS с правильными namespaces
- ✅ Добавит все обязательные iTunes теги
- ✅ Сохранит обновленный RSS

### Шаг 4: Проверить обновленный RSS

```bash
# Проверить наличие обязательных тегов
curl -s https://vlad-podcast-production.up.railway.app/rss.xml | grep -E "language|itunes:image|itunes:explicit"

# Должно показать:
# <language>ru</language>
# <itunes:image href="https://..."/>
# <itunes:explicit>no</itunes:explicit>
```

### Шаг 5: Валидировать RSS фид

Используйте один из валидаторов:

1. **Cast Feed Validator** (рекомендуется для подкастов)
   https://castfeedvalidator.com/
   
2. **Podbase Validator**
   https://podba.se/validate/

3. **W3C Feed Validation**
   https://validator.w3.org/feed/

Вставьте URL: `https://vlad-podcast-production.up.railway.app/rss.xml`

### Шаг 6: Переподписаться в подкаст-приложении

После исправления RSS, **удалите** старую подписку и **добавьте заново**:

#### Apple Podcasts
1. Удалите старую подписку (если была)
2. Library → Shows → "+" → "Add a Show by URL"
3. Вставьте: `https://vlad-podcast-production.up.railway.app/rss.xml`

#### Overcast
1. Удалите старую подписку (если была)  
2. "+" → "Add URL"
3. Вставьте: `https://vlad-podcast-production.up.railway.app/rss.xml`

## Технические детали

### Обязательные теги для iTunes подкастов

На уровне `<channel>`:
- ✅ `<language>` - код языка (например, `ru`, `en`)
- ✅ `<itunes:image>` - URL обложки подкаста
- ✅ `<itunes:author>` - автор подкаста
- ✅ `<itunes:explicit>` - рейтинг контента (`yes`, `no`, `clean`)
- ✅ `<itunes:owner>` - контакты владельца
- ✅ `<itunes:category>` - категория подкаста
- ⚠️ `<itunes:type>` - тип подкаста (`episodic` или `serial`) - опционально

На уровне `<item>`:
- ✅ `<enclosure>` - URL аудио файла
- ✅ `<guid>` - уникальный идентификатор эпизода
- ✅ `<pubDate>` - дата публикации
- ⚠️ `<itunes:duration>` - длительность (HH:MM:SS) - опционально
- ⚠️ `<itunes:image>` - обложка эпизода - опционально

### Правильные XML Namespaces

```xml
<rss 
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:atom="http://www.w3.org/2005/Atom"
  version="2.0">
  <channel>
    <atom:link href="..." rel="self" type="application/rss+xml"/>
    <itunes:author>...</itunes:author>
    <itunes:image href="..."/>
    ...
  </channel>
</rss>
```

**❌ Неправильно:**
```xml
<rss xmlns:ns0="..." xmlns:ns1="...">
  <ns0:link .../>
  <ns1:author>...</ns1:author>
```

**✅ Правильно:**
```xml
<rss xmlns:atom="..." xmlns:itunes="...">
  <atom:link .../>
  <itunes:author>...</itunes:author>
```

## Автоматизация

После исправления, все новые эпизоды будут автоматически добавляться с правильными namespaces, так как код был обновлен:

- ✅ `config.py` - добавлено поле `podcast_image`
- ✅ `web.py` - передает `image_url` в RSSManager
- ✅ `yt2pod.py` - передает `image_url` в RSSManager
- ✅ Все утилиты обновлены

## Troubleshooting

### RSS валидный, но подкаст-приложение не находит фид

1. **Проверьте Content-Type заголовок:**
   ```bash
   curl -I https://vlad-podcast-production.up.railway.app/rss.xml
   ```
   Должен быть: `Content-Type: application/rss+xml`

2. **Проверьте доступность по HTTPS:**
   Подкаст-приложения требуют HTTPS. Railway автоматически предоставляет HTTPS.

3. **Проверьте размер изображения:**
   - Минимум: 1400x1400px
   - Максимум: 3000x3000px
   - Формат: JPG или PNG (не WebP!)

4. **Очистите кэш приложения:**
   Некоторые приложения кэшируют неудачные попытки. Подождите 15-30 минут или переустановите приложение.

### Изображение не отображается

1. Убедитесь, что URL изображения доступен публично:
   ```bash
   curl -I https://your-image-url.jpg
   ```

2. Проверьте формат изображения (JPG/PNG, не WebP)

3. Проверьте, что изображение квадратное и правильного размера

### После обновления старые подписки не видят изменения

Это нормально. Подкаст-приложения кэшируют фиды. Нужно:
1. Удалить старую подписку
2. Подождать несколько минут
3. Добавить подписку заново

## Полезные ссылки

- [Apple Podcasts Requirements](https://podcasters.apple.com/support/823-podcast-requirements)
- [RSS 2.0 Specification](http://www.rssboard.org/rss-specification)
- [iTunes Podcast Tags](https://help.apple.com/itc/podcasts_connect/#/itcb54353390)
- [Cast Feed Validator](https://castfeedvalidator.com/)
