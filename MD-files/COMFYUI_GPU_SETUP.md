# ComfyUI GPU Setup для RTX 3090 - Z-Image Turbo

**Сервер:** `ssh ubuntu@195.209.210.175 -i ~/Desktop/dao-vitteai.pem`
**GPU:** RTX 3090 24GB | Driver: 580.105.08 | CUDA: 13.0
**ComfyUI:** http://195.209.210.175:8188

---

## Быстрый старт

### 1. Создать .env.production
```bash
cd /home/ubuntu/ComfyUI

cat > .env.production <<'EOF'
CUDA_LAUNCH_BLOCKING=1
CUDA_DEVICE_ORDER=PCI_BUS_ID
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True
TORCH_NUM_THREADS=16
NVIDIA_VISIBLE_DEVICES=0
EOF
```

### 2. Обновить systemd service
```bash
sudo tee /etc/systemd/system/comfyui.service > /dev/null <<'EOF'
[Unit]
Description=ComfyUI Production Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ComfyUI
EnvironmentFile=/home/ubuntu/ComfyUI/.env.production
ExecStart=/home/ubuntu/ComfyUI/venv/bin/python /home/ubuntu/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --normalvram --dont-upcast-attention --bf16-unet --disable-cuda-malloc
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/ComfyUI/comfyui_production.log
StandardError=append:/home/ubuntu/ComfyUI/comfyui_production.log

[Install]
WantedBy=multi-user.target
EOF
```

### 3. Перезапустить
```bash
sudo systemctl daemon-reload
sudo systemctl restart comfyui
sudo systemctl status comfyui
nvidia-smi
```

---

## Оптимальные настройки Z-Image Turbo Workflow

### ComfyUI Флаги (уже применены):
- `--normalvram` - оптимально для 24GB
- `--bf16-unet` - скорость без потери качества
- `--dont-upcast-attention` - экономит VRAM
- `--disable-cuda-malloc` - стабильность

### Настройки в workflow:

**UNETLoader (node 1):**
- Model: `moodyPornMix_v7.safetensors`
- weight_dtype: `fp8_e4m3fn` (быстрее в 2x, ~6GB вместо 12GB)

**CLIPLoader (node 2):**
- CLIP: `qwen_3_4b.safetensors`
- Type: `lumina2` ✅
- Device: `cpu` (освобождает 2GB VRAM)

**KSampler (node 8):**
- Steps: `8` (оптимально для Z-Image Turbo)
- CFG: `1.0` ✅
- Sampler: `euler` или `euler_ancestral`
- Scheduler: `simple` или `sgm_uniform`
- Denoise: `1.0`

**ModelSamplingAuraFlow (node 9):**
- Shift: `3.0` (стандарт) или `5.0` (если артефакты)

**LoRA Loader (node 21):**
- Strength: `0.7-0.9` (уменьши если артефакты)

**EmptySD3LatentImage (node 4):**
- Batch size: `1` ✅

---

## Промпты для Z-Image Turbo

### ⚠️ Особенности модели:
- **НЕТ negative prompts** (используй ConditioningZeroOut)
- Любит **описательные предложения**, не теги
- Очень **буквальная** - формулируй точно
- **Чувствительна** к sampler/scheduler

### Пример хорошего промпта:
```
A beautiful young Asian woman in her early twenties stands outdoors on a hot summer afternoon. She has long flowing black hair and an athletic, curvy figure with full breasts and wide hips. She wears a thin white cotton t-shirt that has become completely soaked with water, clinging tightly to her skin and revealing the shape of her body underneath, paired with short denim shorts that sit low on her hips. She holds a melting ice cream cone in her hand, sensually licking it while looking directly at the camera with a seductive smile. The golden hour sunlight creates a warm glow on her porcelain skin. The photograph is taken at eye level, capturing her from head to upper thighs in sharp focus. Professional photography, photorealistic, high detail, natural lighting.
```

### Шаблон промпта:
```
[Описание человека: возраст, внешность, фигура] + [Одежда: детали, состояние] + [Действие: что делает] + [Поза и взгляд] + [Освещение и ракурс] + [Стиль фото]
```

---

## Текущая производительность

| Метрика | Значение |
|---------|----------|
| VRAM idle | 314MB |
| VRAM при генерации | 16.2GB |
| GPU utilization | 95% |
| Temperature | 56°C |
| Power | 320W / 350W |
| **Время генерации** | **8-9 сек** ✅ |

---

## Быстрые команды

```bash
# Проверить статус
sudo systemctl status comfyui

# Посмотреть логи
tail -f /home/ubuntu/ComfyUI/comfyui_production.log

# Перезапустить
sudo systemctl restart comfyui

# Мониторинг GPU
watch -n 1 nvidia-smi

# Проверить API
curl http://localhost:8188/system_stats

# Проверить процесс и флаги
ps aux | grep "python.*main.py" | grep -v grep

# Проверить переменные окружения
cat /proc/$(pgrep -f "python.*main.py")/environ | tr '\0' '\n' | grep -E "CUDA|TORCH|PYTORCH"
```

---

## Troubleshooting

**Медленная генерация (>15 сек):**
1. Проверь sampler: должен быть `euler` или `euler_ancestral`
2. Проверь scheduler: должен быть `simple`
3. Steps: не больше 8
4. Weight dtype: используй `fp8_e4m3fn`

**Артефакты в изображениях:**
1. Увеличь shift до `5.0` в ModelSamplingAuraFlow
2. Уменьши LoRA strength до `0.7`
3. Сделай промпт более описательным и конкретным

**Out of Memory:**
1. Убедись что `PYTORCH_CUDA_ALLOC_CONF` установлена
2. Batch size = 1
3. CLIP на CPU
4. Weight dtype = `fp8_e4m3fn`

---

## Backup настроек

```bash
# Создать backup
tar -czf comfyui_backup_$(date +%Y%m%d).tar.gz \
  /home/ubuntu/ComfyUI/.env.production \
  /etc/systemd/system/comfyui.service \
  /home/ubuntu/ComfyUI/user/default/workflows/

# При восстановлении:
# 1. Переустановить NVIDIA драйвер (580.105.08)
# 2. Восстановить файлы из архива
# 3. sudo systemctl daemon-reload && sudo systemctl restart comfyui
```

---

## Sources
- [Z-Image ComfyUI Docs](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)
- [Z-Image vs SDXL Prompts](https://vocal.media/art/your-sdxl-prompts-are-broken-here-is-how-to-fix-them-for-z-image)
- [Z-Image Turbo Issues 2026](https://medium.com/diffusion-doodles/model-rundown-z-image-turbo-qwen-image-2512-edit-2511-flux-2-dev-fc787f5e87ad)
- [Best Sampler Guide](https://z-image.vip/blog/best-sampler-for-z-image-turbo)
