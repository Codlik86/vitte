# LoRA Reference — Image Generator

## LoRA Params

| Persona | LoRA file | strength_model | strength_clip | sampler |
|---------|-----------|---------------|--------------|---------|
| lina | ameg2_con_char.safetensors | 0.88 | 0.93 | res_multistep |
| marianna | QGVJNVQBYVJ0S2TRKZ005EF980.safetensors | 0.79 | 0.95 | euler |
| mei | zimg_asig2_conchar.safetensors | 0.81 | 0.95 | res_multistep |
| stacey | woman037-zimage.safetensors | 0.85 | 0.98 | res_multistep |
| taya | Elise_XWMB_zimage.safetensors | 0.95 | 0.98 | res_multistep |
| julie | elaravoss.safetensors | 0.93 | 0.99 | res_multistep |
| ash | GF7184J7K4SJJSTY8VJ0VRBTQ0.safetensors | 0.95 | 0.99 | res_multistep |
| anastasia | ULRIKANB_SYNTH_zimg_v1.safetensors | 0.78 | 0.92 | res_multistep |
| sasha | zimg-eurameg1-refine-con-char.safetensors | 0.85 | 0.92 | res_multistep |
| roxy | ChaseInfinity_ZimageTurbo.safetensors | 0.85 | 0.92 | res_multistep |
| pai | DENISE_SYNTH_zimg_v1.safetensors | 0.75 | 0.87 | res_multistep |
| hani | z-3l34n0r.safetensors | 0.80 | 0.85 | res_multistep |
| yuna | nano_Korean.safetensors | 0.95 | 0.99 | res_multistep |

## Trigger Words

| Persona | Trigger |
|---------|---------|
| lina | `ameg2` |
| marianna | `Amanda_Z, a beautiful woman with ginger hair, braided hair, green eyes and full lips` |
| yuna | `e1st_asn` |
| taya | `Elise_XWMB, she has blonde hair` |
| stacey | `woman037` |
| mei | `asig2` |
| ash | `brit-woman` |
| julie | `elvaross` |
| anastasia | *(empty)* |
| sasha | `eurameg1` |
| roxy | `Chase Infinity, African American, young woman` |
| pai | `DENISE` |
| hani | `l34n0r, chubby woman` |

## Notes
- All `model_index: 1` (ZIT) by default
- `model_index: 2` = Moody (used for nude context via `model_override=2`)
- Marianna is the only persona using `euler` sampler (all others use `res_multistep`)
- anastasia has no trigger word
