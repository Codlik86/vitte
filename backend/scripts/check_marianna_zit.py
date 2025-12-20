#!/usr/bin/env python
"""Self-check for Marianna (woman041-zit) Z-Image Turbo injector."""

import os
from pathlib import Path

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "dummy")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "dummy")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/dummy")
os.environ.setdefault("PROXYAPI_API_KEY", "dummy")
os.environ.setdefault("COMFYUI_WORKFLOW_NAME", "zimage_turbo_lora")

from backend.app.services.image_generation import (  # noqa: E402
    DEFAULT_NEGATIVE,
    ImageRequestError,
    _apply_template_values,
    _load_workflow_template,
    find_first_node_id,
)
from backend.app.services.persona_images import PersonaImageConfig  # noqa: E402


def _collect_lora_nodes(workflow: dict) -> list[str]:
    return [
        str(node_id)
        for node_id, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") in {"LoraLoader", "LoraLoaderModelOnly"}
    ]


def main() -> None:
    workflow = _load_workflow_template("zimage_turbo_lora")
    if not workflow:
        raise SystemExit("workflow template is missing")

    prompt = "SCENE: spa lounge. USER INTENT (follow precisely): расслабленная обстановка"
    config = PersonaImageConfig(
        lora_filename="woman041-zit.safetensors",
        prompt_core="Woman041, mature confident woman, elegant natural skin, cinematic portrait, photorealistic, high detail",
        negative_prompt=DEFAULT_NEGATIVE,
        lora_strength_model=0.7,
        lora_strength_clip=0.65,
        quality_lora_filename="Mystic-XXX-ZIT-v2.safetensors",
        quality_lora_strength=0.7,
    )

    try:
        workflow = _apply_template_values(
            workflow,
            prompt=prompt,
            negative_prompt=DEFAULT_NEGATIVE,
            config=config,
            workflow_name="zimage_turbo_lora",
        )
    except ImageRequestError as exc:
        raise SystemExit(f"injector failed: {exc.reason}") from exc

    lora_nodes = _collect_lora_nodes(workflow)
    if len(lora_nodes) < 2:
        raise SystemExit("expected two lora nodes in workflow")

    primary_inputs = workflow[lora_nodes[0]]["inputs"]
    secondary_inputs = workflow[lora_nodes[1]]["inputs"]
    primary_name = primary_inputs.get("lora_name")
    strength = primary_inputs.get("strength_model")
    quality_name = secondary_inputs.get("lora_name")
    quality_strength = secondary_inputs.get("strength_model")

    positive_id = find_first_node_id(workflow, "CLIPTextEncode", title_hints=["positive", "prompt", "clip text encode"])
    positive_text = str(workflow.get(positive_id or "", {}).get("inputs", {}).get("text") or "")

    print("persona=Марианна")
    print("workflow=zimage_turbo_lora")
    print(f"primary_lora={primary_name} strength={strength}")
    print(f"quality_lora={quality_name} strength={quality_strength}")
    print(f"prompt_contains_trigger={'woman041' in positive_text.lower()}")


if __name__ == "__main__":
    main()
