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
    lora_filename="woman549-zit.safetensors",
    trigger_word="woman549",
    master_prompt="masterpiece, best quality, ultra detailed, 8k, photorealistic, cinematic lighting, sharp focus, 超高清, 极致细节, 电影感, 真实感爆棚, 顶级画质, 光影大师, 细腻皮肤, 质感拉满",
    prompt_core="woman549, athletic playful fitness model, toned fit body",
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
        lora_filename="woman549-zit.safetensors",
        trigger_word="woman549",
        master_prompt="Athletic playful fitness model with natural skin and consistent face.",
        prompt_core="woman549, athletic playful fitness model, toned fit body, photorealistic, high detail, 超高清, 极致细节, 电影感, 真实感爆棚, 顶级画质, 光影大师, 细腻皮肤, 质感拉满",
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
        master_prompt="Mature confident woman with elegant natural skin and calm gaze.",
        prompt_core="Woman041, mature confident woman, elegant natural skin, cinematic portrait, masterpiece, best quality, ultra detailed, 8k, photorealistic, cinematic lighting, sharp focus, 超高清, 极致细节, 电影感, 真实感爆棚, 顶级画质, 光影大师, 细腻皮肤, 质感拉满",
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
        master_prompt="Playful romantic woman with warm smile and confident gaze, photorealistic portrait.",
        prompt_core="woman037, playful romantic woman, natural look, photorealistic, high detail, cinematic lighting, sharp focus",
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
        master_prompt="Photorealistic look with natural skin texture and expressive eyes, realistic proportions.",
        prompt_core="dahliamixer, HD portrait photo of a gorgeous blonde supermodel, photorealistic, high detail",
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
