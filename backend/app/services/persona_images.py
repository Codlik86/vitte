# backend/app/services/persona_images.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PersonaImageConfig:
    lora_filename: str
    trigger_word: str
    master_prompt: str
    prompt_core: str
    negative_prompt: str
    lora_strength_model: float = 0.75
    lora_strength_clip: float = 0.7
    quality_lora_filename: str | None = None
    quality_lora_strength: float = 0.7
    default_style: str | None = None
    ksampler_steps: int | None = None
    ksampler_sampler_name: str | None = None


# Без NSFW-тегов в negative (как ты просил). Оставляем техничку против артефактов.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

DEFAULT_IMAGE_CONFIG = PersonaImageConfig(
    lora_filename="Character_Mix_FarrahMixerV2_ZIT.safetensors",
    trigger_word="FarrahMixer",
    master_prompt="gorgeous fitness model",
    prompt_core="ultra realistic, photorealistic, natural skin texture, realistic lighting, high dynamic range, fine details, true-to-life colors, cinematic realism",
    negative_prompt=DEFAULT_NEGATIVE,
    lora_strength_model=0.7,
    lora_strength_clip=0.65,
    quality_lora_filename="Mystic-XXX-ZIT-v2.safetensors",
    quality_lora_strength=0.7,
    default_style=None,
    ksampler_steps=None,
    ksampler_sampler_name=None,
)


PERSONA_CONFIGS: Dict[str, PersonaImageConfig] = {
    "lina": PersonaImageConfig(
        lora_filename="Character_Mix_FarrahMixerV2_ZIT.safetensors",
        trigger_word="FarrahMixer",
        master_prompt="gorgeous fitness model",
        prompt_core="ultra realistic, photorealistic, natural skin texture, realistic lighting, high dynamic range, fine details, true-to-life colors, cinematic realism",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="Mystic-XXX-ZIT-v2.safetensors",
        quality_lora_strength=0.7,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
    ),
    "marianna": PersonaImageConfig(
        lora_filename="woman041-zit.safetensors",
        trigger_word="Woman041",
        master_prompt="gorgeous woman",
        prompt_core="ultra realistic, photorealistic, natural skin texture, realistic lighting, high dynamic range, fine details, true-to-life colors, cinematic realism",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="Mystic-XXX-ZIT-v2.safetensors",
        quality_lora_strength=0.7,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
    ),
    "stacey": PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        trigger_word="woman037",
        master_prompt="gorgeous woman",
        prompt_core="ultra realistic, photorealistic, natural skin texture, realistic lighting, high dynamic range, fine details, true-to-life colors, cinematic realism",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="Mystic-XXX-ZIT-v2.safetensors",
        quality_lora_strength=0.7,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
    ),
    "mei": PersonaImageConfig(
        lora_filename="Character_Mix_DahliaMixerV2_ZIT.safetensors",
        trigger_word="dahliamixer",
        master_prompt="gorgeous blonde supermodel",
        prompt_core="ultra realistic, photorealistic, natural skin texture, realistic lighting, high dynamic range, fine details, true-to-life colors, cinematic realism",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="Mystic-XXX-ZIT-v2.safetensors",
        quality_lora_strength=0.15,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
    ),
}

PERSONA_ALIASES: Dict[str, str] = {
    "default_лина": "lina",
    "лина": "lina",
    "lina": "lina",
    "default_marianna": "marianna",
    "default_марианна": "marianna",
    "марианна": "marianna",
    "marianna": "marianna",
    "maria": "marianna",
    "default_стейси": "stacey",
    "стейси": "stacey",
    "stacey": "stacey",
    "stacy": "stacey",
    "default_mei": "mei",
    "default_мей": "mei",
    "мей": "mei",
    "mei": "mei",
}


def resolve_persona_key(name: str | None) -> str | None:
    key = (name or "").strip().lower()
    if not key:
        return None
    if key in PERSONA_CONFIGS:
        return key
    return PERSONA_ALIASES.get(key)


def get_persona_image_config(persona_key: str | None, persona_name: str | None) -> PersonaImageConfig:
    resolved = resolve_persona_key(persona_key) or resolve_persona_key(persona_name)
    return PERSONA_CONFIGS.get(resolved or "", DEFAULT_IMAGE_CONFIG)
