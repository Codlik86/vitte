## Image Pipeline Notes

- Default ComfyUI workflow: `zimage_turbo_lora` (file: `backend/app/assets/comfyui/workflows/zimage_turbo_lora.json`). Set `COMFYUI_WORKFLOW_NAME=sdxl_lora` to use the legacy alias file.
- Default models: `models/checkpoints/huslyorealismxl_v2.safetensors` for SDXL checkpoints; `models/diffusion_models/z_image_turbo_bf16.safetensors`, `models/text_encoders/qwen_3_4b.safetensors`, `models/vae/ae.safetensors` for Z-Image Turbo; LoRAs live in `models/loras/`.
- Multi-LoRA injector: primary persona LoRA is always applied; optional `quality_lora_filename`/`quality_lora_strength` add a secondary LoRA when provided in persona config.
- Prompts are injected into positive CLIP text nodes; negative prompt is applied when a negative CLIP node exists (otherwise the template negative is left untouched).
- Workflows are selected via env and cached per file; bad templates fail fast with `ImageRequestError("bad_workflow_template")`.
