"""
ComfyUI REST API Client
Handles communication with ComfyUI server on GPU
"""
import asyncio
import json
import random
from pathlib import Path
from typing import Dict, Optional, Any
import aiohttp

from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__)


class ComfyUIClient:
    """Client for ComfyUI REST API"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize ComfyUI client.

        Args:
            base_url: ComfyUI server URL (if None, will be assigned from pool)
        """
        self.base_url = base_url or config.COMFYUI_BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=config.GENERATION_TIMEOUT)

    async def load_workflow(self, workflow_path: Path) -> Dict[str, Any]:
        """
        Load workflow JSON from file.

        Args:
            workflow_path: Path to workflow JSON file

        Returns:
            Workflow dict
        """
        try:
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
            logger.info(f"Loaded workflow from {workflow_path}")
            return workflow
        except Exception as e:
            logger.error(f"Failed to load workflow from {workflow_path}: {e}")
            raise

    def modify_workflow(
        self,
        workflow: Dict[str, Any],
        prompt: str,
        seed: Optional[int] = None,
        lora_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Modify workflow with custom prompt, seed, and per-persona LoRA params.
        Also injects CacheDiT Accelerator node for faster generation.

        Args:
            workflow: Base workflow dict
            prompt: Positive prompt text
            seed: Random seed (generated if not provided)
            lora_params: Dict with lora_name, strength_model, strength_clip, sampler_name

        Returns:
            Modified workflow dict
        """
        # Generate random seed if not provided
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        # Find and modify prompt nodes
        # Universal workflow: node "14" = positive, node "15" = negative
        # Positive prompt is the first CLIPTextEncode encountered
        first_clip_seen = False
        for node_id, node_data in workflow.items():
            if node_data.get("class_type") == "CLIPTextEncode":
                if not first_clip_seen:
                    # First CLIPTextEncode = positive prompt
                    workflow[node_id]["inputs"]["text"] = prompt
                    logger.debug(f"Updated positive prompt in node {node_id}")
                    first_clip_seen = True
                # Leave negative prompt as-is (empty string in universal flow)

        # Find and modify KSampler seed and sampler_name
        for node_id, node_data in workflow.items():
            if node_data.get("class_type") == "KSampler":
                workflow[node_id]["inputs"]["seed"] = seed
                logger.debug(f"Updated seed to {seed} in node {node_id}")
                if lora_params and "sampler_name" in lora_params:
                    workflow[node_id]["inputs"]["sampler_name"] = lora_params["sampler_name"]
                    logger.debug(f"Updated sampler_name to {lora_params['sampler_name']} in node {node_id}")

        # Find and modify LoraLoader with persona-specific params
        if lora_params:
            for node_id, node_data in workflow.items():
                if node_data.get("class_type") == "LoraLoader":
                    workflow[node_id]["inputs"]["lora_name"] = lora_params["lora_name"]
                    workflow[node_id]["inputs"]["strength_model"] = lora_params["strength_model"]
                    workflow[node_id]["inputs"]["strength_clip"] = lora_params["strength_clip"]
                    logger.debug(f"Updated LoRA in node {node_id}: {lora_params['lora_name']}")

        # Inject CacheDiT Accelerator between model source and KSampler
        workflow = self._inject_cachedit(workflow)

        return workflow

    def _inject_cachedit(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject CacheDiT_Model_Optimizer node between the model source and KSampler.
        This gives ~1.5x speedup for Z-Image Turbo.
        """
        # Find KSampler node
        ksampler_id = None
        for node_id, node_data in workflow.items():
            if node_data.get("class_type") == "KSampler":
                ksampler_id = node_id
                break

        if not ksampler_id:
            logger.warning("CacheDiT: KSampler not found, skipping injection")
            return workflow

        # Get model source from KSampler (e.g. ["13", 0] = LoraLoader output)
        model_source = workflow[ksampler_id]["inputs"].get("model")
        if not model_source:
            logger.warning("CacheDiT: KSampler has no model input, skipping")
            return workflow

        # Pick a unique node ID that doesn't conflict
        existing_ids = set(int(k) for k in workflow.keys() if k.isdigit())
        cachedit_id = str(max(existing_ids) + 1) if existing_ids else "100"

        # Add CacheDiT node
        workflow[cachedit_id] = {
            "inputs": {
                "model": model_source,  # Takes model from where KSampler was getting it
                "enable": True,
                "model_type": "Auto",
                "warmup_steps": 0,
                "skip_interval": 0,
                "print_summary": True,
            },
            "class_type": "CacheDiT_Model_Optimizer",
            "_meta": {
                "title": "⚡ CacheDiT Accelerator"
            }
        }

        # Redirect KSampler model input to CacheDiT output
        workflow[ksampler_id]["inputs"]["model"] = [cachedit_id, 0]

        logger.info(f"CacheDiT: injected node {cachedit_id} between {model_source[0]} and KSampler {ksampler_id}")

        return workflow

    async def queue_prompt(self, workflow: Dict[str, Any]) -> Optional[str]:
        """
        Queue a prompt for generation in ComfyUI.

        Args:
            workflow: Complete workflow dict

        Returns:
            Prompt ID if successful, None otherwise
        """
        url = f"{self.base_url}/prompt"
        payload = {"prompt": workflow}

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        prompt_id = result.get("prompt_id")
                        logger.info(f"Queued prompt with ID: {prompt_id}")
                        return prompt_id
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to queue prompt: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get generation history for a prompt ID.

        Args:
            prompt_id: Prompt ID from queue_prompt

        Returns:
            History dict or None
        """
        url = f"{self.base_url}/history/{prompt_id}"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        history = await response.json()
                        return history.get(prompt_id)
                    else:
                        logger.error(f"Failed to get history: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return None

    async def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 2.0,
        max_wait: int = 120
    ) -> bool:
        """
        Wait for image generation to complete.

        Args:
            prompt_id: Prompt ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            True if completed successfully, False otherwise
        """
        elapsed = 0
        while elapsed < max_wait:
            history = await self.get_history(prompt_id)

            if history:
                # Check if generation is complete
                status = history.get("status", {})
                if status.get("completed", False):
                    logger.info(f"Generation {prompt_id} completed")
                    return True

                # Check for errors
                if "error" in history:
                    logger.error(f"Generation {prompt_id} failed: {history['error']}")
                    return False

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        logger.error(f"Generation {prompt_id} timed out after {max_wait}s")
        return False

    async def get_image_path(self, prompt_id: str) -> Optional[str]:
        """
        Get the file path of generated image.

        Args:
            prompt_id: Prompt ID

        Returns:
            Image filename or None
        """
        history = await self.get_history(prompt_id)
        if not history:
            return None

        # Extract image info from outputs
        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                images = node_output["images"]
                if images:
                    # Return first image filename
                    return images[0].get("filename")

        return None

    async def download_image(self, filename: str) -> Optional[bytes]:
        """
        Download generated image from ComfyUI.

        Args:
            filename: Image filename from get_image_path

        Returns:
            Image bytes or None
        """
        url = f"{self.base_url}/view"
        params = {
            "filename": filename,
            "type": "output",
            "subfolder": ""
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        logger.info(f"Downloaded image: {filename} ({len(image_data)} bytes)")
                        return image_data
                    else:
                        logger.error(f"Failed to download image: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    async def generate_image(
        self,
        workflow_path: Path,
        prompt: str,
        seed: Optional[int] = None,
        lora_params: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """
        Complete image generation pipeline.

        Args:
            workflow_path: Path to workflow JSON
            prompt: Positive prompt text
            seed: Random seed (optional)
            lora_params: Per-persona LoRA params (lora_name, strength_model, strength_clip, sampler_name)

        Returns:
            Image bytes or None
        """
        try:
            logger.info(f"Starting generation on {self.base_url}")

            # Load and modify workflow
            workflow = await self.load_workflow(workflow_path)
            workflow = self.modify_workflow(workflow, prompt, seed, lora_params)

            # Queue prompt
            prompt_id = await self.queue_prompt(workflow)
            if not prompt_id:
                return None

            # Wait for completion
            success = await self.wait_for_completion(prompt_id)
            if not success:
                return None

            # Get image path
            filename = await self.get_image_path(prompt_id)
            if not filename:
                logger.error("No image filename in history")
                return None

            # Download image
            image_data = await self.download_image(filename)
            return image_data

        except Exception as e:
            logger.error(f"Error in generate_image pipeline on {self.base_url}: {e}")
            return None
