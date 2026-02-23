# LoRA Inference Server — План реализации

## Проблема
ComfyUI перезагружает модель при каждой смене LoRA → колд старт ~5 секунд.
Цель: переключение между персонажами без перезагрузки модели.

---

## Решение
Заменить ComfyUI API на кастомный **FastAPI сервис на diffusers**, который:
- Держит base model постоянно в VRAM
- Загружает все LoRA один раз при старте
- Переключает LoRA через `set_adapters()` без перезагрузки (~0 сек)

---

## Инфраструктура

### Текущая схема
```
Бот (CPU контейнер) → ComfyUI :8188 (zimage)
Бот (CPU контейнер) → ComfyUI :8189 (moody)
```

### Новая схема
```
Бот (CPU контейнер) → FastAPI :8818 (zimage diffusers сервис)
Бот (CPU контейнер) → FastAPI :8819 (moody diffusers сервис)
```

---

## Сервер

- OS: Ubuntu
- ComfyUI path: `/home/comfyui/`
- Python venv: `/home/comfyui/venv/`

---

## Модели

### Z-Image Turbo сервис (порт 8818)
| Тип | Файл | Путь |
|-----|------|------|
| Diffusion model | `z_image_turbo_bf16.safetensors` | `/home/comfyui/models/diffusion_models/` |
| CLIP | `qwen_3_4b.safetensors` | `/home/comfyui/models/clip/` |
| VAE | `ae.safetensors` | `/home/comfyui/models/vae/` |

### MoodyPornMix сервис (порт 8819)
| Тип | Файл | Путь |
|-----|------|------|
| Diffusion model | `moodyPornMix_v7.safetensors` | `/home/comfyui/models/diffusion_models/` |
| CLIP | `qwen_3_4b.safetensors` | `/home/comfyui/models/clip/` |
| VAE | `ae.safetensors` | `/home/comfyui/models/vae/` |

---

## LoRA (одинаковые для обоих сервисов)

Путь: `/home/comfyui/models/loras/`

| adapter_name | Файл |
|---|---|
| `ChaseInfinity` | `ChaseInfinity_ZimageTurbo.safetensors` |
| `DENISE` | `DENISE_SYNTH_zimg_v1.safetensors` |
| `Elise` | `Elise_XWMB_zimage.safetensors` |
| `GF7184` | `GF7184J7K4SJJSTY8VJ0VRBTQ0.safetensors` |
| `QGVJNV` | `QGVJNVQBYVJ0S2TRKZ005EF980.safetensors` |
| `RealisticSnapshot` | `RealisticSnapshot-Zimage-Turbov5.safetensors` |
| `ULRIKANB` | `ULRIKANB_SYNTH_zimg_v1.safetensors` |
| `ameg2` | `ameg2_con_char.safetensors` |
| `elaravoss` | `elaravoss.safetensors` |
| `nano_Korean` | `nano_Korean.safetensors` |
| `woman037` | `woman037-zimage.safetensors` |
| `z_3l34n0r` | `z-3l34n0r.safetensors` |
| `zimg_eurameg1` | `zimg-eurameg1-refine-con-char.safetensors` |
| `zimg_asig2` | `zimg_asig2_conchar.safetensors` |

> ⚠️ Исключить из загрузки: `CoolShot_2000s_qwen.safetensors`, `analogcore2000s_qwen.safetensors` — это CLIP LoRA, не character.

---

## Параметры генерации (из текущего ComfyUI воркфлоу)

| Параметр | Значение |
|---|---|
| steps | 8 |
| cfg | 1.0 |
| sampler | `res_multistep` |
| scheduler | `sgm_uniform` |
| denoise | 1.0 |
| width | 1024 |
| height | 1024 |
| batch_size | 1 |

---

## API Endpoints

### POST `/generate`

**Request:**
```json
{
  "prompt": "girl, solo, ...",
  "negative_prompt": "",
  "lora_name": "ameg2",
  "lora_strength": 0.95,
  "width": 1024,
  "height": 1024,
  "steps": 8,
  "cfg": 1.0,
  "seed": -1
}
```

**Response:**
```json
{
  "image": "<base64 encoded PNG>",
  "seed": 2987654321
}
```

### GET `/health`
Проверка статуса сервиса — загружена ли модель, список доступных LoRA.

### GET `/loras`
Список загруженных adapter_name.

---

## Структура файлов

```
/home/comfyui/inference_server/
├── server.py           # основной FastAPI сервис
├── model_manager.py    # загрузка модели и LoRA, set_adapters логика
├── requirements.txt    # зависимости
├── start_zimage.sh     # запуск сервиса для zimage на порту 8818
└── start_moody.sh      # запуск сервиса для moody на порту 8819
```

---

## Ключевая логика (model_manager.py)

```python
# При старте — загружаем модель один раз
pipeline = load_pipeline(model_path, clip_path, vae_path)

# Загружаем все LoRA один раз
for adapter_name, lora_file in LORAS.items():
    pipeline.load_lora_weights(lora_path, adapter_name=adapter_name)

# При каждом запросе — только меняем активный адаптер (без перезагрузки)
pipeline.set_adapters([lora_name], adapter_weights=[lora_strength])
image = pipeline(prompt, ...).images[0]
```

---

## Зависимости (requirements.txt)

```
fastapi
uvicorn
diffusers>=0.27.0
transformers
torch
accelerate
peft
safetensors
Pillow
```

---

## Запуск

```bash
# Z-Image сервис
MODEL=z_image_turbo_bf16 PORT=8818 python server.py

# Moody сервис  
MODEL=moodyPornMix_v7 PORT=8819 python server.py
```

---

## Важные нюансы для реализации

1. **Z-Image Turbo** — нестандартная архитектура (ZImage/DiT), нужно проверить совместимость с diffusers. Возможно потребуется `from_single_file()` с указанием типа модели.

2. **CLIP qwen_3_4b** — это Qwen2 text encoder, не стандартный CLIP. Загружать через `AutoTokenizer` + `AutoModel` или через diffusers `CLIPTextModel` с `trust_remote_code=True`.

3. **sampler `res_multistep`** — нестандартный семплер из ComfyUI. В diffusers ближайший аналог — `DPMSolverMultistepScheduler` или `EulerDiscreteScheduler`. Нужно подобрать.

4. **set_adapters ограничение** — все LoRA должны быть одинаковой архитектуры (rank). У Z-Image LoRA судя по размерам файлов (~170MB) rank одинаковый — должно работать. Два файла по ~47MB (`_qwen`) исключены намеренно.

5. **Память** — модель ~12GB bf16 + 14 LoRA по ~170MB = ~14.4GB. На 48GB VRAM влезает с запасом, оба сервиса одновременно тоже (~29GB суммарно).

6. **Конкурентные запросы** — добавить очередь (asyncio.Queue или простой Lock) чтобы set_adapters не конфликтовал между запросами.

---

## Что остаётся неизвестным (уточнить при реализации)

- Точный способ загрузки Z-Image Turbo через diffusers (может потребоваться кастомный pipeline)
- Соответствие ComfyUI семплера `res_multistep` → diffusers scheduler
- Нужна ли авторизация на эндпоинтах
