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
    lora_strength_model: float = 1.0
    lora_strength_clip: float = 1.0
    default_style: str | None = None
    ksampler_steps: int | None = None
    ksampler_sampler_name: str | None = None
    ksampler_scheduler: str | None = None
    auraflow_shift: float | int | None = None


# Без NSFW-тегов в negative (как ты просил). Оставляем техничку против артефактов.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

DEFAULT_IMAGE_CONFIG = PersonaImageConfig(
    lora_filename="Character_Mix_FarrahMixerV2_ZIT.safetensors",
    trigger_word="FarrahMixer",
    master_prompt="gorgeous fitness model",
    prompt_core="medium long shot, upper body to thighs",
    negative_prompt=DEFAULT_NEGATIVE,
    lora_strength_model=1.0,
    lora_strength_clip=1.0,
    default_style=None,
    ksampler_steps=None,
    ksampler_sampler_name=None,
    ksampler_scheduler="simple",
    auraflow_shift=7.0,
)


PERSONA_CONFIGS: Dict[str, PersonaImageConfig] = {
    "lina": PersonaImageConfig(
        lora_filename="Character_Mix_FarrahMixerV2_ZIT.safetensors",
        trigger_word="FarrahMixer",
        master_prompt="gorgeous fitness model",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=1.0,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
        ksampler_scheduler="simple",
        auraflow_shift=7.0,
    ),
    "marianna": PersonaImageConfig(
        lora_filename="woman041-zit.safetensors",
        trigger_word="Woman041",
        master_prompt="gorgeous woman",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=1.0,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
        ksampler_scheduler="simple",
        auraflow_shift=7.0,
    ),
    "stacey": PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        trigger_word="woman037",
        master_prompt="gorgeous blondy woman",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.79,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=12,
        ksampler_sampler_name="dpmpp_sde",
        ksampler_scheduler="beta",
        auraflow_shift=6.0,
    ),
    "mei": PersonaImageConfig(
        lora_filename="Character_Mix_DahliaMixerV2_ZIT.safetensors",
        trigger_word="dahliamixer",
        master_prompt="gorgeous blonde supermodel",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=1.0,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
        ksampler_scheduler="simple",
        auraflow_shift=7.0,
    ),
    "taya": PersonaImageConfig(
        lora_filename="isabella.safetensors",
        trigger_word="<ISABELL_ID>",
        master_prompt="beautiful woman with long, dark hair and warm brown eyes",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=1.0,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
        ksampler_scheduler="simple",
        auraflow_shift=7.0,
    ),
    "ash": PersonaImageConfig(
        lora_filename="KawaiiKinkyNE_extracted_lora_ratio_rank_adaptive_ratio_0.15_fp16.safetensors",
        trigger_word="gorgeous asian woman",
        master_prompt="expressive fiery asian empathetic woman, natural skin, photorealistic, consistent face",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=1.0,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=16,
        ksampler_sampler_name="euler",
        ksampler_scheduler="simple",
        auraflow_shift=7.0,
    ),
    "julie": PersonaImageConfig(
        lora_filename="EmmaNotreal - Z-Image-Turbo.safetensors",
        trigger_word="young Dutch blondy woman",
        master_prompt="gorgeous blondy woman",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.8,
        default_style=None,
        ksampler_steps=12,
        ksampler_sampler_name="dpmpp_2s_ancestral",
        ksampler_scheduler="beta",
        auraflow_shift=6.0,
    ),
    "yuna": PersonaImageConfig(
        lora_filename="nano_Korean.safetensors",
        trigger_word="e1st_asn",
        master_prompt="gentle Korean-looking young woman",
        prompt_core="medium long shot, upper body to thighs",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.8,
        lora_strength_clip=1.0,
        default_style=None,
        ksampler_steps=9,
        ksampler_sampler_name="dpmpp_2m_sde",
        ksampler_scheduler="beta",
        auraflow_shift=6.0,
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
    "default_эш": "ash",
    "эш": "ash",
    "ash": "ash",
    "default_джули": "julie",
    "джули": "julie",
    "julie": "julie",
    "default_тая": "taya",
    "тая": "taya",
    "taya": "taya",
    "юна": "yuna",
    "yuna": "yuna",
    "default_юна": "yuna",
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
