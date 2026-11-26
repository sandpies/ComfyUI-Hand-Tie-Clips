# What each feature needs

The Starter workflow's note lists the files a plain chain run loads. This page covers everything else: each optional feature, what it needs, and the folder each file goes in. Leave out anything you don't use. A feature whose files are missing either stays hidden, shows **missing: …** in its tab, or stops before the first hop and names the file.

Folders are under `ComfyUI/models/` unless a row says otherwise.

## The base chain (always)

| What | File | Folder |
|---|---|---|
| DiT | [`minimax_h3_ref2va_int8_convrot`](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/diffusion_models/minimax_h3_ref2va_int8_convrot.safetensors), or the 8-step baked [CleanTie / HandTie / SilkTie](https://huggingface.co/sandpies/cleantie-v2Sing-hybrid) (`silktie_v2Sing_eros_8step_int8_minmaxxed` / `w6_g16_hq` / `bf16`) | `diffusion_models` |
| Text encoder | [`qwen3vl_32b_minimax_h3_int8_convrot`](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors) | `text_encoders` |
| Video VAE | [`minimax_h3_video_vae_fp16`](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/vae/minimax_h3_video_vae_fp16.safetensors) or [`minimax_h3_lynnreal_light_vae_int8_convrot`](https://huggingface.co/Kijai/MiniMax-H3-experimental/blob/main/minimax_h3_lynnreal_light_vae_int8_convrot.safetensors) | `vae` |
| Audio VAE | [`minimax_h3_audio_vae_fp32`](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/vae/minimax_h3_audio_vae_fp32.safetensors) | `vae` |

`HTC Sparse Attention`, `H3 Token LoRA` and the AdaLN fix are built into this pack. Sparse Attention runs on Comfy Kitchen (`comfy_kitchen`), which comes with a current ComfyUI; update ComfyUI if the node reports it missing.

## Finishing (RUN tab)

| Feature | Needs | Folder |
|---|---|---|
| Upsample size-up | [`minimax_h3_latent_upscaler_3d_conv_v1_bf16`](https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler/blob/main/minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_bf16.safetensors), or the 2D [`minimax_h3_latent_upscaler_2d_conv_v1_bf16`](https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler/blob/main/minimax_h3_latent_upscaler_2d_conv_v1/minimax_h3_latent_upscaler_2d_conv_v1_bf16.safetensors) (takes `sharpness` 1-6) | `latent_upscale_models` |
| Upsample re-draw `regen2k` (default) | [`open_h3_regenerate_2k_r256pp_bf16`](https://huggingface.co/sandpies/ComfyUI-H3-Video-Upsampler/blob/main/lora/open_h3_regenerate_2k_r256pp_bf16.safetensors) (3.77 GB) | `loras` |
| Upsample re-draw `ic` | [`minimax_h3_open_regenerate_2k_ic_lora_avg_rank_21_bf16`](https://huggingface.co/Kijai/MiniMax-H3-experimental/blob/main/loras/minimax_h3_open_regenerate_2k_ic_lora_avg_rank_21_bf16.safetensors) + [`minimax_h3_hyperflow_8step_v1.0`](https://huggingface.co/videorebirth/hyperflow/blob/main/minimax_h3_hyperflow_8step_v1.0.safetensors) (+ [`minimax_h3_lms_v1.0_r64`](https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/blob/main/loras/minimax_h3_lms_v1.0_r64.safetensors) if you have it), on the plain unpruned `minimax_h3_ref2va_*` DiT with no LoRAs wired to `upsample_dit`. No text encoder loads unless `clip` is wired. | `loras` |
| Small-face pass (`face_pass`) | YuNet face detector (`face_detection_yunet_2023mar.onnx`, 232 KB). It downloads itself once; offline, put it where the console line says. Needs `opencv-python` (`cv2`). | pack folder |
| Upsample `chunk_join = windowed` | A ComfyUI with MiniMax H3 context windows (Comfy-Org/ComfyUI#17425). No file. | — |
| Frame generation (`HTC Save Video`, `frame_gen x2`) | RTX GPU + the `nvidia-vfx` package ([ComfyUI_Nvidia_VFX_Nodes](https://github.com/Comfy-Org/ComfyUI_Nvidia_VFX_Nodes) installs it) | — |
| Live preview | [`taeh3`](https://huggingface.co/Kijai/MiniMax-H3-TAE/blob/main/vae_approx/taeh3.safetensors) + [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) (Model Preview Override) | `vae_approx` |

## Writing help: WRITE tab, SandTie (STANDARD tab / `SandTiePromptRig`), Studio lyrics

These call a **local language model** that you run yourself, on any server that answers the OpenAI chat API (`/v1/chat/completions`): LM Studio, llama.cpp's `llama-server`, Ollama, KoboldCpp, vLLM, and so on. Set the address and model in the writer settings on the WRITE tab (the Studio tab's **⚙ LLM Settings** opens the same settings). Nothing is downloaded by the pack, and the render works without one.

- **Context size.** WRITE's instructions alone are about 12k tokens. Load the model with **16k context at least**, 32k for plans of many hops. A turn that cannot fit is refused before it is sent, and the message names the size to set. That check only works on servers that report their loaded context (LM Studio does). **Ollama** doesn't, and its default context can be small enough to trim WRITE's instructions without an error, so raise it yourself: set `OLLAMA_CONTEXT_LENGTH=16384` (or more) before starting Ollama, or put `PARAMETER num_ctx 16384` in the model's Modelfile.
- **Pictures.** Eye Scan (describing a reference or RefMod), reading the start image in WRITE, and SWAP's scene reading send pictures to the writer, so they need a **vision model** (any "VL" / vision build). With a text-only model those steps return an error or are skipped; the rest works.
- **Unload for renders.** The writer is asked to unload before a render starts so H3 gets the card back. A server that cannot unload in place keeps its VRAM; close it yourself before queueing if the render runs out of memory.

## SWAP tab (one-hop person swap or scene edit)

| Needs | Folder |
|---|---|
| [`viggle_remake_swap_comfyui`](https://huggingface.co/Viggle/Viggle-Remake/blob/main/comfyui/viggle_remake_swap_comfyui.safetensors) (person / head swap) and [`viggle_remake_edit_comfyui`](https://huggingface.co/Viggle/Viggle-Remake/blob/main/comfyui/viggle_remake_edit_comfyui.safetensors) (scene edit), 3.77 GB each. The node loads the right one. | `loras` |

## RefMod tab

| Feature | Needs | Folder |
|---|---|---|
| Building, editing and stitching RefMods (**Shots → Sheet**) | Nothing extra: the stitcher uses no model. | — |
| Subject cut-out (blurred background) | A SAM checkpoint (`sam_vit_h` / `_l` / `_b`) and the `segment_anything` package; without them it falls back to `rembg` (`pip install rembg`, which fetches its `isnet-general-use` model once). | `sams` |
| RefLoRA files | Your own LoRAs. | `loras` |
| Eye Scan | A vision writer model (see *Writing help*). | — |
| **Sheet → Single Shot** and asset images (Image Forge) | One image engine from the next section. | — |

## Image Forge (RefMod Sheet → Single Shot, Studio asset images, SWAP stills)

The tab lists every engine below and marks the ones whose files it finds as ready; a missing engine shows exactly which files it lacks. **One is enough.** All need a current ComfyUI (the image nodes are core).

| Engine | Model (`diffusion_models`) | Text encoder (`text_encoders`) | VAE (`vae`) | LoRA (`loras`) |
|---|---|---|---|---|
| Qwen 2.1 + Viggle Turbo, 6-step (default) | [`qwen_image_2.1_int8_convrot`](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors) | [`qwen3vl_8b_int8_convrot`](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors) | [`qwen_image_2.1_vae_bf16`](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/main/vae/qwen_image_2.1_vae_bf16.safetensors) | [`Qwen-Image-2.1-viggle-turbo-v0.3-6step-lora-r128`](https://huggingface.co/Viggle/Qwen-Image-2.1-viggle-turbo/blob/main/Qwen-Image-2.1-viggle-turbo-v0.3-6step-lora-r128.safetensors) |
| Qwen 2.1 Turbo, 8-step | [`qwen_image_2.1_turbo_int8_convrot`](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/main/diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors) | same | same | — |
| Qwen 2.1 Base, 25-step | `qwen_image_2.1_int8_convrot` | same | same | — |
| Unlocked RedQW2.1, 12-step | `redgptK2T2W6A8REDQW21_redqw21UNLOCKEDV2_int8` ([zombothe26/redqw21](https://huggingface.co/zombothe26/redqw21)) | `qwen3-vl-8b-int8_convrot_simple` or `qwen3vl_8b_int8_convrot` | same | — |
| MOSS-Image (text to image only, no edit) | [`moss_image_sft_int8_convrot`](https://huggingface.co/Comfy-Org/MOSS-Image/blob/main/diffusion_models/moss_image_sft_int8_convrot.safetensors) | [`qwen3.5_9b_int8_convrot`](https://huggingface.co/Comfy-Org/MOSS-Image/blob/main/text_encoders/qwen3.5_9b_int8_convrot.safetensors) | [`flux2-vae`](https://huggingface.co/Comfy-Org/MOSS-Image/blob/main/vae/flux2-vae.safetensors) | optional DMD LoRA |
| MiniMax-H3-Image, 6-step | [`minimax_h3_image_pruned_int8_convrot`](https://huggingface.co/Comfy-Org/MiniMax-H3-Image/blob/main/diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors) (21 GB; `w4a8` 12.6 GB) | the chain's `qwen3vl_32b_minimax_h3_*` | [`minimax_h3_image_vae_fp16`](https://huggingface.co/Comfy-Org/MiniMax-H3-Image/blob/main/vae/minimax_h3_image_vae_fp16.safetensors) | — |
| MiniMax-H3-Image pDMD, 4-step | same | same | same | `minimax_h3_pdmd_2nfe_comfyui` |
| MiniMax-H3-Image Character Swap | same | same | same | `h3_character_swap_v1.5` (or [`h3_image_character_swap_v1`](https://huggingface.co/akatz-ai/MiniMax-H3-Image-Character-Swap-LoRA)) |
| P-H3-Image, 8-step (+ pDMD 4-step) | `p-h3-image_int8_convrot`, or the chain's `minimax_h3_fl2va_pruned_int8_convrot` + `p-h3-image_lora_bf16` | `p-h3-image_text_encoder_int8_convrot` | `p-h3-image_vae_int8_convrot` | pDMD: `minimax_h3_pdmd_2nfe_comfyui` |
| PlagueKind H3-ImageEdit, 10-step | `minimax_h3_fl2va_pruned_int8_convrot` + `p-h3-image_lora_bf16` | the chain's `qwen3vl_32b_minimax_h3_*` | `minimax_h3_lynnreal_light_vae_int8_convrot` + `p-h3-image_vae_int8_convrot` | — |

The Qwen 2.1 rows are the lightest (about 7 GB model + 9 GB encoder). The H3-Image rows reuse the chain's 32B text encoder.

## Studio tab (music videos)

| Feature | Needs | Folder |
|---|---|---|
| Concept and lyrics | A local writer model (see *Writing help*). | — |
| Song generation | YuE2: either ComfyUI's core YuE2 nodes or [pytraveler/YuE2-ComfyUI](https://github.com/pytraveler/YuE2-ComfyUI), plus [`yue2_3b_int8_convrot`](https://huggingface.co/Comfy-Org/YuE2/blob/main/checkpoints/yue2_3b_int8_convrot.safetensors) (3.96 GB) | `checkpoints` |
| Song → sheet (ABC) | Core `SheetSage2AudioToABC` + [`sheetsage2_bf16`](https://huggingface.co/Comfy-Org/YuE2/blob/main/audio_encoders/sheetsage2_bf16.safetensors) | `audio_encoders` |
| Asset images | An Image Forge engine (above). | — |
| Beat / section editor | Nothing extra. | — |

## Audio: song measuring, lip-sync, dialogue

**The pack never downloads these by itself.** Fetch them once, using ComfyUI's own Python (portable install: `python_embeded\python.exe`):

```bash
# vocal separator (HDemucs, goes in the torch hub cache)
python -c "import torchaudio; torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS.get_model()"
# Whisper (goes in the Hugging Face cache)
hf download openai/whisper-small
```

| Feature | Needs | Without it |
|---|---|---|
| Lip-sync to vocals (`dialogue_audio_file = auto:vocals`) | HDemucs | The mouths follow the full mix; the console says so. |
| Studio **Listen** / song measuring (lyric lines, vocal sections) | HDemucs + Whisper, plus `transformers` | It measures tempo and bars from the mix only, with no lyric timing. |
| `dialogue_lock` with no `dialogue_audio_file` | Whisper (`whisper-small`; tiny / base / medium / large-v3-turbo also work) | The run stops before the first hop and names the file. |
| `dialogue_audio_file` = your own vocal stem or line recording | Nothing extra. | — |

## Steering dials (`HTCSteeringDials`)

The five dials (`htc_motion`, `htc_expression`, `htc_energy`, `htc_life`, `htc_sound`) are built on your machine the first time you use them with `clip` wired to the H3 text encoder, and saved in `models/loras/dials/`. Nothing to download. `HTCMakeSteeringDial` builds your own from `A ||| B` prompt pairs the same way.

## Hand-tie previs (`pin_mech = hand_tie`)

Any `qwen3vl_4b*` or `qwen3vl_8b*` text encoder in `text_encoders` (e.g. [`qwen3vl_4b_fp8_scaled`](https://huggingface.co/Comfy-Org/Krea-2/resolve/main/text_encoders/qwen3vl_4b_fp8_scaled.safetensors) or [`qwen3vl_8b_int8_convrot`](https://huggingface.co/Comfy-Org/Qwen-Image-2.1/blob/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors), which the Qwen Image Forge engines also use).
