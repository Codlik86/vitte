# Извлечение Seed из ComfyUI изображений

## Как это работает

ComfyUI не хранит метаданные в классическом формате A1111. Вместо этого в PNG-чанки записывается **полный JSON workflow** — граф всех нод. Seed находится внутри объекта KSampler → inputs → seed.

Важно: метаданные сохраняются **только в PNG**. Если картинки были пересохранены в JPEG/WebP — данные потеряны. Переименование файлов метаданные не затрагивает.

---

## Скрипт extract_seeds.py

Приложенный скрипт — самый быстрый способ пройтись по папке. Кидаешь его рядом с картинками и запускаешь:

```bash
pip install Pillow
python extract_seeds.py /путь/к/папке
```

Без аргументов сканирует текущую директорию. На выходе — таблица: имя файла, тип ноды, seed.

Скрипт находит все варианты KSampler (включая KSamplerAdvanced и кастомные ноды с "sampler" в имени), вытаскивает поля `seed` и `noise_seed`.

---

## Готовый софт

### Standalone (без ComfyUI)

**SD Prompt Reader** — лучший вариант для просмотра вне ComfyUI.
- GitHub: github.com/receyuki/stable-diffusion-prompt-reader
- Установка: `pip install sd-prompt-reader`
- GUI приложение с drag & drop, показывает prompt, seed, steps, CFG, sampler
- Есть CLI для батч-обработки
- Поддерживает A1111, ComfyUI, NAI, и другие форматы
- Ограничение: сложные воркфлоу с кастомными нодами могут не распарситься

**Prompting Pixels Metadata Viewer** — веб-утилита, ничего ставить не надо.
- Сайт: promptingpixels.com/metadata
- Drag & drop прямо в браузере, всё обрабатывается локально
- Поддерживает A1111, ComfyUI, SwarmUI, Midjourney

### Ноды внутри ComfyUI

Если нужно прямо в воркфлоу:

- **DP Get Seed From Image** (ComfyUI-Desert-Pixel-Nodes) — специализированная нода для извлечения seed из метаданных или тензора изображения
- **Load Image with Metadata (Crystools)** — замена стандартной Load Image, вытаскивает prompt, seed и весь workflow
- **ComfyUI Prompt Reader Node** — нод-версия SD Prompt Reader, максимальная совместимость с разными форматами
- **ComfyUI-ImageWithMetadata** — батч-загрузка с извлечением seed, steps, CFG, prompt
- **ComfyUI-SaveImageWithMetaData** — сохраняет в A1111-совместимом формате (полезно для будущих генераций, чтобы seed читался любым инструментом)

---

## Drag & Drop в ComfyUI

Самый примитивный способ: перетащить PNG в интерфейс ComfyUI. Он восстановит весь воркфлоу с seed в KSampler. Работает, но только по одной картинке за раз.

---

## Рекомендации

1. **Для быстрой проверки одной картинки** — drag & drop в ComfyUI или Prompting Pixels
2. **Для пачки файлов** — скрипт extract_seeds.py или SD Prompt Reader CLI
3. **Для интеграции в воркфлоу** — DP Get Seed From Image нода
4. **На будущее** — используй ComfyUI-SaveImageWithMetaData вместо стандартного Save Image. Он записывает seed прямо в A1111-совместимые метаданные, и потом любой инструмент его прочитает без парсинга workflow JSON
5. **Батчи** — если генерил через batch (не queue), индивидуальные сиды для каждого изображения в батче НЕ сохраняются. Сохраняется только начальный seed для всего батча
