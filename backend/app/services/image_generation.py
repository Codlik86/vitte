# backend/app/services/image_generation.py
from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import httpx
from aiogram import Bot
from aiogram.types import BufferedInputFile

from ..config import settings
from ..db import get_session
from ..logging_config import logger
from ..models import AccessStatus, Persona, User
from ..services.access import get_active_subscription
from ..services.analytics import log_event
from ..services.image_quota import consume_image, get_image_quota
from .persona_images import PersonaImageConfig, get_persona_image_config

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / "assets" / "comfyui" / "workflows" / "sdxl_lora.json"

# Без NSFW-тегов (как ты просил) — только техничка.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

MAX_PROMPT_LEN = 240
MAX_HINT_LEN = 160
POLL_INTERVAL = 1.0
RETRIES = 2

_workflow_cache: Dict[str, Any] | None = None
_semaphore = asyncio.Semaphore(max(int(getattr(settings, "comfyui_concurrency", 1) or 1), 1))


@dataclass
class GenerationPlan:
    user_id: int
    chat_id: int
    persona_id: int
    persona_key: str | None
    persona_name: str | None
    prompt: str
    negative_prompt: str
    config: PersonaImageConfig
    has_subscription: bool


def _load_workflow_template() -> Dict[str, Any]:
    """
    Loads and caches workflow JSON template from WORKFLOW_PATH.
    Returns a deep copy every time (safe to mutate).
    """
    global _workflow_cache
    if _workflow_cache is None:
        try:
            _workflow_cache = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.error("ComfyUI workflow template not found at %s", WORKFLOW_PATH)
            _workflow_cache = {}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to read workflow template %s: %s", WORKFLOW_PATH, exc)
            _workflow_cache = {}
    return json.loads(json.dumps(_workflow_cache))


def _apply_template_values(
    template: Dict[str, Any],
    *,
    prompt: str,
    negative_prompt: str,
    config: PersonaImageConfig,
) -> Dict[str, Any]:
    """
    Applies ckpt/lora/prompt/seed to the expected node IDs:
      3: CheckpointLoaderSimple
      4: LoraLoader
      5: CLIPTextEncode (positive)
      6: CLIPTextEncode (negative)
      8: KSampler
    """
    workflow = json.loads(json.dumps(template))

    checkpoint_name = settings.comfyui_default_checkpoint or workflow.get("3", {}).get("inputs", {}).get("ckpt_name")
    seed = random.randint(1, 2_000_000_000)

    try:
        if checkpoint_name:
            workflow["3"]["inputs"]["ckpt_name"] = checkpoint_name

        workflow["4"]["inputs"]["lora_name"] = config.lora_filename
        workflow["4"]["inputs"]["strength_model"] = float(config.lora_strength_model)
        workflow["4"]["inputs"]["strength_clip"] = float(config.lora_strength_clip)

        workflow["5"]["inputs"]["text"] = prompt
        workflow["6"]["inputs"]["text"] = negative_prompt or DEFAULT_NEGATIVE

        workflow["8"]["inputs"]["seed"] = seed
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to apply workflow template values: %s", exc)

    return workflow


def _build_prompt_hint(context: dict[str, Any], persona: Persona | None) -> str:
    reply = (context.get("reply_text") or "").strip()
    user_message = (context.get("user_message") or "").strip()
    source = reply or user_message

    hint = source.replace("\n", " ").replace("\r", " ").strip()
    if len(hint) > MAX_HINT_LEN:
        hint = hint[:MAX_HINT_LEN].rsplit(" ", 1)[0]

    if not hint and persona:
        hint = (persona.short_description or persona.name or "").strip()

    return hint


def _build_full_prompt(config: PersonaImageConfig, hint: str) -> str:
    """
    prompt_core + (optional hint) + (optional default_style)
    """
    style = f", {config.default_style}" if config.default_style else ""
    trimmed_hint = hint.strip(" .,")

    pieces = [config.prompt_core]
    if trimmed_hint:
        pieces.append(trimmed_hint)

    prompt = ", ".join(pieces) + style
    return prompt[:MAX_PROMPT_LEN]


async def _prepare_generation(
    user_id: int,
    persona_id: int,
    chat_id: int,
    context: dict[str, Any],
) -> GenerationPlan | None:
    every_n = max(int(getattr(settings, "image_every_n_bot_replies", 0) or 0), 0)
    cooldown_seconds = max(int(getattr(settings, "image_cooldown_seconds", 0) or 0), 0)

    if every_n <= 0:
        return None

    # Группы/каналы имеют отрицательный chat_id — вырубаем тут на всякий.
    if chat_id < 0:
        return None

    async for session in get_session():
        user = await session.get(User, user_id)
        persona = await session.get(Persona, persona_id) if persona_id else None
        if not user or not persona:
            return None

        counter = int(user.bot_reply_counter or 0)
        # Генерим на каждом N-м ответе бота (3,6,9...)
        if counter == 0 or (counter % every_n) != 0:
            return None

        now = datetime.utcnow()
        if user.last_image_sent_at and cooldown_seconds > 0:
            if now - user.last_image_sent_at < timedelta(seconds=cooldown_seconds):
                return None

        has_subscription = bool(
            user.access_status == AccessStatus.SUBSCRIPTION_ACTIVE
            or await get_active_subscription(session, user.id)
        )

        quota = await get_image_quota(session, user, has_subscription=has_subscription)
        if quota.get("total_remaining", 0) <= 0:
            await log_event(session, user.id, "image_failed", {"reason": "no_quota", "persona_id": persona.id})
            await session.commit()
            return None

        config = get_persona_image_config(persona.key, persona.name)
        hint = _build_prompt_hint(context, persona)
        prompt = _build_full_prompt(config, hint)
        negative_prompt = (config.negative_prompt or DEFAULT_NEGATIVE).strip()

        # Ставим timestamp сразу, чтобы не спамить при параллельных сообщениях
        user.last_image_sent_at = now
        await log_event(
            session,
            user.id,
            "image_requested",
            {"persona_id": persona.id, "persona_key": persona.key, "counter": counter},
        )
        await session.commit()

        return GenerationPlan(
            user_id=user.id,
            chat_id=chat_id,
            persona_id=persona.id,
            persona_key=persona.key,
            persona_name=persona.name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            config=config,
            has_subscription=has_subscription,
        )

    return None


async def request_comfyui(workflow_payload: Dict[str, Any]) -> bytes:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        raise RuntimeError("COMFYUI_BASE_URL is not configured")

    timeout_seconds = float(getattr(settings, "comfyui_timeout_seconds", 90) or 90)
    timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        last_error: Exception | None = None

        for attempt in range(1, RETRIES + 2):
            try:
                resp = await client.post(f"{base_url}/prompt", json={"prompt": workflow_payload})
                resp.raise_for_status()

                payload = resp.json() or {}
                prompt_id = payload.get("prompt_id") or payload.get("promptId")
                if not prompt_id:
                    raise RuntimeError("No prompt_id in ComfyUI response")

                image_info = await _wait_for_image(client, base_url, str(prompt_id))
                return await _download_image(client, base_url, image_info)

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= (RETRIES + 1):
                    break
                await asyncio.sleep(1.5 * attempt)

        raise last_error or RuntimeError("Unknown ComfyUI error")


async def _wait_for_image(client: httpx.AsyncClient, base_url: str, prompt_id: str) -> dict:
    deadline = time.monotonic() + float(getattr(settings, "comfyui_timeout_seconds", 90) or 90)

    while time.monotonic() < deadline:
        resp = await client.get(f"{base_url}/history/{prompt_id}")
        resp.raise_for_status()

        data = resp.json() or {}
        record = data.get(prompt_id) or {}
        outputs = record.get("outputs") or {}

        for node in outputs.values():
            images = node.get("images") or []
            if images:
                return images[0]

        await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError("ComfyUI generation timed out")


async def _download_image(client: httpx.AsyncClient, base_url: str, image_info: dict) -> bytes:
    filename = image_info.get("filename")
    subfolder = image_info.get("subfolder", "")
    file_type = image_info.get("type", "output")

    if not filename:
        raise RuntimeError("ComfyUI returned empty filename")

    params = {"filename": filename}
    if subfolder:
        params["subfolder"] = subfolder
    if file_type:
        params["type"] = file_type

    resp = await client.get(f"{base_url}/view", params=params)
    resp.raise_for_status()
    return resp.content


async def _deliver_image(plan: GenerationPlan, image_bytes: bytes, bot_instance: Bot) -> None:
    async for session in get_session():
        user = await session.get(User, plan.user_id)
        if not user:
            return

        try:
            await consume_image(session, user, count=1, has_subscription=plan.has_subscription)
            user.last_image_sent_at = datetime.utcnow()
            await log_event(
                session,
                user.id,
                "image_generated",
                {"persona_id": plan.persona_id, "persona_key": plan.persona_key},
            )
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to persist image usage for user %s: %s", plan.user_id, exc)
            await session.rollback()
            raise

    input_file = BufferedInputFile(image_bytes, filename="vitte_image.png")
    await bot_instance.send_photo(plan.chat_id, input_file)


async def _generate_and_send(plan: GenerationPlan, context: dict[str, Any], bot_instance: Bot) -> None:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        logger.info("ComfyUI base URL is not configured; skipping image generation")
        async for session in get_session():
            try:
                await log_event(session, plan.user_id, "image_failed", {"reason": "not_configured", "persona_id": plan.persona_id})
                await session.commit()
            except Exception:
                pass
        return

    template = _load_workflow_template()
    workflow = _apply_template_values(
        template,
        prompt=plan.prompt,
        negative_prompt=plan.negative_prompt,
        config=plan.config,
    )

    ckpt_name = workflow.get("3", {}).get("inputs", {}).get("ckpt_name")
    logger.info(
        "ComfyUI request user=%s persona=%s ckpt=%s lora=%s strengths=(%.2f/%.2f)",
        plan.user_id,
        plan.persona_id,
        ckpt_name,
        plan.config.lora_filename,
        plan.config.lora_strength_model,
        plan.config.lora_strength_clip,
    )

    try:
        async with _semaphore:
            image_bytes = await request_comfyui(workflow_payload=workflow)
        await _deliver_image(plan, image_bytes, bot_instance)

    except Exception as exc:  # noqa: BLE001
        logger.error("Image generation/delivery failed user=%s persona=%s: %s", plan.user_id, plan.persona_id, exc)
        async for session in get_session():
            try:
                await log_event(session, plan.user_id, "image_failed", {"reason": "generation_error", "persona_id": plan.persona_id})
                await session.commit()
            except Exception:
                pass


async def maybe_generate_and_send_image(
    user_id: int,
    chat_id: int,
    persona_id: int,
    bot_instance: Bot,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Called after sending a text reply. Schedules async generation without blocking chat flow.
    """
    if not getattr(settings, "image_enabled", False):
        return

    ctx = context or {}

    try:
        plan = await _prepare_generation(user_id, persona_id, chat_id, ctx)
        if not plan:
            return

        asyncio.create_task(
            _generate_and_send(plan, ctx, bot_instance),
            name=f"image-gen-{user_id}-{persona_id}",
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to schedule image generation user=%s persona=%s: %s", user_id, persona_id, exc)
