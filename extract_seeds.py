"""
Извлекает seed из KSampler метаданных ComfyUI PNG-файлов.

Использование:
    python extract_seeds.py [путь_к_папке]

Если путь не указан — сканирует текущую директорию.
Зависимости: pip install Pillow
"""

import json
import sys
from pathlib import Path
from PIL import Image


def extract_seeds(image_path: Path) -> list[dict]:
    """Извлекает все seed из KSampler нод в PNG-метаданных ComfyUI."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        return [{"error": f"Не удалось открыть: {e}"}]

    prompt_raw = img.info.get("prompt")
    if not prompt_raw:
        return [{"error": "Нет метаданных ComfyUI (поле 'prompt' отсутствует)"}]

    try:
        prompt_data = json.loads(prompt_raw)
    except json.JSONDecodeError:
        return [{"error": "Невалидный JSON в метаданных"}]

    results = []
    for node_id, node in prompt_data.items():
        class_type = node.get("class_type", "")
        if "ksampler" in class_type.lower() or "sampler" in class_type.lower():
            inputs = node.get("inputs", {})
            seed = inputs.get("seed") or inputs.get("noise_seed")
            if seed is not None:
                results.append({
                    "node_id": node_id,
                    "class_type": class_type,
                    "seed": seed,
                })

    if not results:
        return [{"error": "KSampler нода не найдена в workflow"}]

    return results


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    if not folder.is_dir():
        print(f"Ошибка: '{folder}' не является директорией")
        sys.exit(1)

    pngs = sorted(folder.glob("*.png"))
    if not pngs:
        print(f"PNG-файлы не найдены в '{folder}'")
        sys.exit(1)

    print(f"Найдено {len(pngs)} PNG-файлов\n")
    print(f"{'Файл':<40} {'Нода':<25} {'Seed'}")
    print("-" * 90)

    for png in pngs:
        seeds = extract_seeds(png)
        for entry in seeds:
            if "error" in entry:
                print(f"{png.name:<40} {'—':<25} ⚠ {entry['error']}")
            else:
                print(f"{png.name:<40} {entry['class_type']:<25} {entry['seed']}")


if __name__ == "__main__":
    main()
