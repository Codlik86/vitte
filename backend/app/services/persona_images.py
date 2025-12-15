# backend/app/services/persona_images.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PersonaImageConfig:
    lora_filename: str
    prompt_core: str
    negative_prompt: str
    lora_strength_model: float = 0.75
    lora_strength_clip: float = 0.7
    default_style: str | None = None


# Без NSFW-тегов в negative (как ты просил). Оставляем техничку против артефактов.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

DEFAULT_IMAGE_CONFIG = PersonaImageConfig(
    lora_filename="woman033.safetensors",
    prompt_core=(
        "woman033, photorealistic young woman, consistent face, natural body, "
        "natural skin texture, 85mm lens, high detail"
    ),
    negative_prompt=DEFAULT_NEGATIVE,
    lora_strength_model=0.7,
    lora_strength_clip=0.65,
    default_style=None,
)


PERSONA_IMAGE_CONFIGS: Dict[str, PersonaImageConfig] = {
    # Лина: используем твою LoRA woman033 + триггер word "woman033"
    # ВАЖНО: lora_filename только имя файла, без подпапок.
    "default_лина": PersonaImageConfig(
        lora_filename="woman033.safetensors",
        prompt_core=(
            "woman033, photorealistic young woman, consistent face, natural body, "
            "natural skin texture, 85mm lens, high detail"
        ),
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        default_style=None,
    ),
    # На всякий — алиасы по имени (если persona.key не префиксный)
    "лина": PersonaImageConfig(
        lora_filename="woman033.safetensors",
        prompt_core=(
            "woman033, photorealistic young woman, consistent face, natural body, "
            "natural skin texture, 85mm lens, high detail"
        ),
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        default_style=None,
    ),
    "lina": PersonaImageConfig(
        lora_filename="woman033.safetensors",
        prompt_core=(
            "woman033, photorealistic young woman, consistent face, natural body, "
            "natural skin texture, 85mm lens, high detail"
        ),
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        default_style=None,
    ),

    "default_марианна": PersonaImageConfig(
        lora_filename="marianna.safetensors",
        prompt_core="photorealistic mature confident woman, elegant look, natural skin, cinematic portrait, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        default_style=None,
    ),
    "default_аки": PersonaImageConfig(
        lora_filename="aki.safetensors",
        prompt_core="anime-inspired girl, dark hair, subtle blush, poised thoughtful expression, clean high quality",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.65,
        lora_strength_clip=0.6,
        default_style=None,
    ),
}


def get_persona_image_config(persona_key: str | None, persona_name: str | None) -> PersonaImageConfig:
    key = (persona_key or "").strip().lower()
    name = (persona_name or "").strip().lower()
    # часто key бывает типа default_лина — оставляем как есть, но даём fallback на имя
    return PERSONA_IMAGE_CONFIGS.get(key) or PERSONA_IMAGE_CONFIGS.get(name) or DEFAULT_IMAGE_CONFIG
