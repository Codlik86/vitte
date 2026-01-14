#!/usr/bin/env python
"""Quick smoke test for Z-Image Turbo multi-LoRA injection."""

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

    prompt = "SCENE: sauna. USER INTENT (follow precisely): покажи спину"
    config = PersonaImageConfig(
        lora_filename="woman037-zimage.safetensors",
        prompt_core="woman037 smoke test",
        negative_prompt=DEFAULT_NEGATIVE,
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
    assert len(lora_nodes) >= 2, "expected two lora nodes in workflow"

    primary_inputs = workflow[lora_nodes[0]]["inputs"]
    secondary_inputs = workflow[lora_nodes[1]]["inputs"]
    assert primary_inputs.get("lora_name") == Path(config.lora_filename).name, "primary lora mismatch"
    assert secondary_inputs.get("lora_name") == Path(config.quality_lora_filename).name, "quality lora mismatch"

    positive_id = find_first_node_id(workflow, "CLIPTextEncode", title_hints=["positive", "prompt", "clip text encode"])
    assert positive_id, "positive text node not found"
    positive_text = str(workflow[positive_id]["inputs"].get("text") or "").lower()
    assert "sauna" in positive_text, "scene text missing in prompt"
    assert "покажи спину" in positive_text, "user intent missing in prompt"

    negative_id = find_first_node_id(workflow, "CLIPTextEncode", title_hints=["negative"])
    if negative_id:
        neg_text = str(workflow[negative_id]["inputs"].get("text") or "").strip()
        assert neg_text, "negative prompt empty"

    print("ok: zimage_turbo injector applied")


if __name__ == "__main__":
    main()
