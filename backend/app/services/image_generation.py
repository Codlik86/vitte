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
from aiogram.types import BufferedInputFile

from ..bot import bot
from ..config import settings
from ..config.persona_images import PersonaImageConfig, get_persona_image_config
from ..db import get_session
from ..logging_config import logger
from ..models import AccessStatus, Persona, User
from ..services.access import get_active_subscription
from ..services.analytics import log_event
from ..services.image_quota import consume_image, get_image_quota

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / "assets" / "comfyui" / "workflows" / "sdxl_lora.json"
DEFAULT_NEGATIVE = "nsfw, nude, naked, explicit, lowres, blurry, deformed hands, extra fingers, text, watermark, logo"
MAX_PROMPT_LEN = 240
MAX_HINT_LEN = 160
POLL_INTERVAL = 1.0
RETRIES = 2

_workflow_cache: Dict[str, Any] | None = None
_semaphore = asyncio.Semaphore(max(settings.comfyui_concurrency, 1))


@dataclass
class GenerationPlan:
    user_id: int  # database id
    chat_id: int  # telegram chat id
    persona_id: int
    persona_key: str | None
    persona_name: str | None
    prompt: str
    negative_prompt: str
    config: PersonaImageConfig
    has_subscription: bool


def _load_workflow_template() -> Dict[str, Any]:
    global _workflow_cache
    if _workflow_cache is None:
        try:
            _workflow_cache = json.loads(WORKFLOW_PATH.read_text())
        except FileNotFoundError:
            logger.error("ComfyUI workflow template not found at %s", WORKFLOW_PATH)
            _workflow_cache = {}
    return json.loads(json.dumps(_workflow_cache))


def _deep_update(target: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target


def _apply_template_values(
    template: Dict[str, Any],
    *,
    prompt: str,
    negative_prompt: str,
    config: PersonaImageConfig,
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    workflow = json.loads(json.dumps(template))
    checkpoint_name = settings.comfyui_default_checkpoint or workflow.get("3", {}).get("inputs", {}).get("ckpt_name")
    seed = random.randint(1, 2_000_000_000)

    try:
        workflow["3"]["inputs"]["ckpt_name"] = checkpoint_name
        workflow["4"]["inputs"]["lora_name"] = config.lora_filename
        workflow["4"]["inputs"]["strength_model"] = config.lora_strength_model
        workflow["4"]["inputs"]["strength_clip"] = config.lora_strength_clip
        workflow["5"]["inputs"]["text"] = prompt
        workflow["6"]["inputs"]["text"] = negative_prompt or DEFAULT_NEGATIVE
        workflow["8"]["inputs"]["seed"] = seed
    except Exception as exc:  # noqa: BLE001 - defensive against malformed templates
        logger.error("Failed to apply workflow template overrides: %s", exc)

    if overrides:
        _deep_update(workflow, overrides)
    return workflow


def _build_prompt_hint(context: dict[str, Any], persona: Persona | None) -> str:
    reply = (context.get("reply_text") or "").strip()
    user_message = (context.get("user_message") or "").strip()
    source = reply or user_message
    hint = source.replace("\n", " ").replace("\r", " ")
    if len(hint) > MAX_HINT_LEN:
        hint = hint[:MAX_HINT_LEN].rsplit(" ", 1)[0]
    if not hint and persona:
        hint = persona.short_description or persona.name or ""
    return hint


def _build_full_prompt(config: PersonaImageConfig, hint: str) -> str:
    style = f", {config.default_style}" if config.default_style else ""
    core = config.prompt_core
    trimmed_hint = hint.strip(" .")
    pieces = [core]
    if trimmed_hint:
        pieces.append(trimmed_hint)
    prompt = ", ".join(pieces) + style
    prompt = prompt[:MAX_PROMPT_LEN]
    return prompt


async def _prepare_generation(
    user_id: int,
    persona_id: int,
    chat_id: int,
    context: dict[str, Any],
) -> GenerationPlan | None:
    every_n = max(settings.image_every_n_bot_replies, 0)
    cooldown_seconds = max(settings.image_cooldown_seconds, 0)
    if every_n <= 0:
        return None

    async for session in get_session():
        user = await session.get(User, user_id)
        persona = await session.get(Persona, persona_id) if persona_id else None
        if not user or not persona:
            return None

        counter = user.bot_reply_counter or 0
        if counter == 0 or counter % every_n != 0:
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
        if quota["total_remaining"] <= 0:
            await log_event(
                session,
                user.id,
                "image_failed",
                {"reason": "no_quota", "persona_id": persona.id},
            )
            await session.commit()
            return None

        config = get_persona_image_config(persona.key, persona.name)
        hint = _build_prompt_hint(context, persona)
        prompt = _build_full_prompt(config, hint)
        negative_prompt = config.negative_prompt or DEFAULT_NEGATIVE

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


async def request_comfyui(
    prompt: str,
    negative_prompt: str,
    workflow_template: Dict[str, Any] | None = None,
    overrides: Dict[str, Any] | None = None,
) -> bytes:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        raise RuntimeError("COMFYUI_BASE_URL is not configured")

    template = workflow_template or _load_workflow_template()
    workflow = _apply_template_values(
        template,
        prompt=prompt,
        negative_prompt=negative_prompt,
        config=get_persona_image_config(None, None),
        overrides=overrides,
    )

    timeout = httpx.Timeout(settings.comfyui_timeout_seconds, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        last_error: Exception | None = None
        for attempt in range(1, RETRIES + 2):
            try:
                response = await client.post(f"{base_url}/prompt", json={"prompt": workflow})
                response.raise_for_status()
                payload = response.json()
                prompt_id = payload.get("prompt_id") or payload.get("promptId")
                if not prompt_id:
                    raise RuntimeError("No prompt_id in ComfyUI response")
                image_info = await _wait_for_image(client, base_url, prompt_id)
                return await _download_image(client, base_url, image_info)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt > RETRIES + 1:
                    break
                await asyncio.sleep(1.5 * attempt)
        raise last_error or RuntimeError("Unknown ComfyUI error")


async def _wait_for_image(client: httpx.AsyncClient, base_url: str, prompt_id: str) -> dict:
    deadline = time.monotonic() + settings.comfyui_timeout_seconds
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


async def _deliver_image(
    plan: GenerationPlan,
    image_bytes: bytes,
) -> None:
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
    try:
        await bot.send_photo(plan.chat_id, input_file)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send image to user %s: %s", plan.user_id, exc)
        async for session in get_session():
            try:
                await log_event(
                    session,
                    plan.user_id,
                    "image_failed",
                    {"reason": "send_error", "persona_id": plan.persona_id},
                )
                await session.commit()
            except Exception:
                pass


async def _generate_and_send(plan: GenerationPlan, context: dict[str, Any]) -> None:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        logger.info("ComfyUI base URL is not configured; skipping image generation")
        async for session in get_session():
            try:
                await log_event(
                    session,
                    plan.user_id,
                    "image_failed",
                    {"reason": "not_configured", "persona_id": plan.persona_id},
                )
                await session.commit()
            except Exception:
                pass
        return
    overrides = {
        "4": {
            "inputs": {
                "lora_name": plan.config.lora_filename,
                "strength_model": plan.config.lora_strength_model,
                "strength_clip": plan.config.lora_strength_clip,
            }
        },
        "3": {"inputs": {"ckpt_name": settings.comfyui_default_checkpoint}},
        "5": {"inputs": {"text": plan.prompt}},
        "6": {"inputs": {"text": plan.negative_prompt}},
    }
    template = _load_workflow_template()
    try:
        async with _semaphore:
            image_bytes = await request_comfyui(
                plan.prompt,
                plan.negative_prompt,
                workflow_template=template,
                overrides=overrides,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Image generation failed for user %s persona %s: %s", plan.user_id, plan.persona_id, exc)
        async for session in get_session():
            try:
                await log_event(
                    session,
                    plan.user_id,
                    "image_failed",
                    {"reason": "generation_error", "persona_id": plan.persona_id},
                )
                await session.commit()
            except Exception:
                pass
        return

    try:
        await _deliver_image(plan, image_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.error("Image delivery failed for user %s persona %s: %s", plan.user_id, plan.persona_id, exc)
        async for session in get_session():
            try:
                await log_event(
                    session,
                    plan.user_id,
                    "image_failed",
                    {"reason": "delivery_error", "persona_id": plan.persona_id},
                )
                await session.commit()
            except Exception:
                pass


async def maybe_generate_and_send_image(
    user_id: int,
    chat_id: int,
    persona_id: int,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Entry point invoked after sending a text reply. Schedules async generation without blocking chat flow.
    """
    if not settings.image_enabled:
        return
    ctx = context or {}
    try:
        plan = await _prepare_generation(user_id, persona_id, chat_id, ctx)
        if not plan:
            return
        asyncio.create_task(
            _generate_and_send(plan, ctx),
            name=f"image-gen-{user_id}-{persona_id}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to schedule image generation for user %s persona %s: %s", user_id, persona_id, exc)
