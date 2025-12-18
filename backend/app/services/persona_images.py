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
    quality_lora_filename: str | None = None
    quality_lora_strength: float = 0.5
    default_style: str | None = None


# Без NSFW-тегов в negative (как ты просил). Оставляем техничку против артефактов.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

DEFAULT_IMAGE_CONFIG = PersonaImageConfig(
    lora_filename="woman549-zit.safetensors",
    prompt_core="woman549, athletic playful fitness model, toned fit body, photorealistic, high detail",
    negative_prompt=DEFAULT_NEGATIVE,
    lora_strength_model=0.7,
    lora_strength_clip=0.65,
    quality_lora_filename="b3tternud3s_v3.safetensors",
    quality_lora_strength=0.45,
    default_style=None,
)


PERSONA_IMAGE_CONFIGS: Dict[str, PersonaImageConfig] = {
    # Лина (woman549) для Z-Image Turbo
    "default_лина": PersonaImageConfig(
        lora_filename="woman549-zit.safetensors",
        prompt_core="woman549, athletic playful fitness model, toned fit body, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.45,
        default_style=None,
    ),
    "лина": PersonaImageConfig(
        lora_filename="woman549-zit.safetensors",
        prompt_core="woman549, athletic playful fitness model, toned fit body, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.45,
        default_style=None,
    ),
    "lina": PersonaImageConfig(
        lora_filename="woman549-zit.safetensors",
        prompt_core="woman549, athletic playful fitness model, toned fit body, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.45,
        default_style=None,
    ),

    "default_стейси": PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        prompt_core="woman037, warm masseuse with gentle smile, toned feminine figure, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.5,
        default_style=None,
    ),
    "стейси": PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        prompt_core="woman037, warm masseuse with gentle smile, toned feminine figure, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.5,
        default_style=None,
    ),
    "stacey": PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        prompt_core="woman037, warm masseuse with gentle smile, toned feminine figure, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.5,
        default_style=None,
    ),
    "stacy": PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        prompt_core="woman037, warm masseuse with gentle smile, toned feminine figure, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.5,
        default_style=None,
    ),

    "default_марианна": PersonaImageConfig(
        lora_filename="woman041-zit.safetensors",
        prompt_core="Woman041, mature confident woman, elegant natural skin, cinematic portrait, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.45,
        default_style=None,
    ),
    "марианна": PersonaImageConfig(
        lora_filename="woman041-zit.safetensors",
        prompt_core="Woman041, mature confident woman, elegant natural skin, cinematic portrait, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.45,
        default_style=None,
    ),
    "marianna": PersonaImageConfig(
        lora_filename="woman041-zit.safetensors",
        prompt_core="Woman041, mature confident woman, elegant natural skin, cinematic portrait, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="b3tternud3s_v3.safetensors",
        quality_lora_strength=0.45,
        default_style=None,
    ),
}


def get_persona_image_config(persona_key: str | None, persona_name: str | None) -> PersonaImageConfig:
    key = (persona_key or "").strip().lower()
    name = (persona_name or "").strip().lower()
    # часто key бывает типа default_лина — оставляем как есть, но даём fallback на имя
    return PERSONA_IMAGE_CONFIGS.get(key) or PERSONA_IMAGE_CONFIGS.get(name) or DEFAULT_IMAGE_CONFIG
