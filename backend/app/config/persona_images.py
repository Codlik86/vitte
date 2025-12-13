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


DEFAULT_IMAGE_CONFIG = PersonaImageConfig(
    lora_filename="generic.safetensors",
    prompt_core="cinematic portrait of a warm, friendly woman looking at the camera, soft light, detailed face, inviting smile",
    negative_prompt="nsfw, nude, naked, explicit, lowres, blurry, deformed hands, extra fingers, worst quality, watermark, text, logo",
    lora_strength_model=0.6,
    lora_strength_clip=0.55,
    default_style="cozy room, shallow depth of field, natural skin, gentle mood",
)


PERSONA_IMAGE_CONFIGS: Dict[str, PersonaImageConfig] = {
    # Keys can be persona.key or persona.name lowercased for convenience.
    "default_лина": PersonaImageConfig(
        lora_filename="lina.safetensors",
        prompt_core="fitness muse girl at the gym, energetic pose, athletic build, glossy skin, playful smile, cinematic rim light",
        negative_prompt=DEFAULT_IMAGE_CONFIG.negative_prompt,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        default_style="modern gym background, neon highlights, sweat sheen, bokeh lights",
    ),
    "default_марианна": PersonaImageConfig(
        lora_filename="marianna.safetensors",
        prompt_core="mature confident woman, elegant look, intense eyes, soft smile, alluring but tasteful, premium portrait",
        negative_prompt=DEFAULT_IMAGE_CONFIG.negative_prompt,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        default_style="warm apartment evening light, cozy armchair, cinematic shadows",
    ),
    "default_аки": PersonaImageConfig(
        lora_filename="aki.safetensors",
        prompt_core="stylish anime-inspired girl with dark hair, subtle blush, poised and thoughtful, sleek casual outfit",
        negative_prompt=DEFAULT_IMAGE_CONFIG.negative_prompt,
        lora_strength_model=0.65,
        lora_strength_clip=0.6,
        default_style="night city lights, soft neon reflections, shallow depth of field",
    ),
}


def get_persona_image_config(persona_key: str | None, persona_name: str | None) -> PersonaImageConfig:
    key = (persona_key or "").lower()
    name = (persona_name or "").lower()
    return PERSONA_IMAGE_CONFIGS.get(key) or PERSONA_IMAGE_CONFIGS.get(name) or DEFAULT_IMAGE_CONFIG
