"""Painted cartoon backgrounds with a free open model, CPU only (GitHub runner).

  python gen_bg.py <jobs.json> <out_dir> [index]

jobs.json: [{"name": "bedroom_night", "prompt": "...", "seeds": [1, 2], "w": 768, "h": 1344}, ...]
Model: SDXL base 1.0 (CreativeML Open RAIL++-M: commercial use allowed under its use restrictions) with the
ByteDance SDXL-Lightning 4-step UNet (same licence family). 4 steps, guidance 0, so a 768x1344 image takes a few minutes
on 4 CPU cores. Characters are NOT generated: every prompt asks for an empty set; the cast is animated in code on top.
"""
import json
import os
import sys
import time
from pathlib import Path

import torch
from diffusers import EulerDiscreteScheduler, StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline, UNet2DConditionModel
from PIL import Image
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

STYLE = ("hand-drawn 2D cartoon background illustration, comic book style with clean dark ink outlines, warm cinematic "
         "lighting, rich detail, soft painted shading, cozy, high quality animation background art, empty scene, no people, "
         "no characters, no text, no letters, no watermark")
NEG = "people, person, human, character, face, text, letters, words, watermark, logo, signature, photo, photorealistic, blurry"


def main():
    jobs = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 3:
        jobs = [jobs[int(sys.argv[3])]]
    torch.set_num_threads(int(os.environ.get("THREADS", "4")))
    base = "stabilityai/stable-diffusion-xl-base-1.0"
    unet = UNet2DConditionModel.from_config(base, subfolder="unet")
    unet.load_state_dict(load_file(hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors")))
    pipe = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, torch_dtype=torch.float32)
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
    pipe.set_progress_bar_config(disable=True)
    for j in jobs:
        for seed in j.get("seeds", [1]):
            t0 = time.time()
            if j.get("init"):                                  # repaint an existing picture: keeps its layout, changes its style
                i2i = StableDiffusionXLImg2ImgPipeline(**pipe.components)
                init = Image.open(j["init"]).convert("RGB").resize((j.get("w", 768), j.get("h", 1344)))
                img = i2i(prompt=f"{j['prompt']}, {STYLE}", image=init, strength=j.get("strength", 0.6), num_inference_steps=8,
                          guidance_scale=0, generator=torch.Generator().manual_seed(seed)).images[0]
            else:
                img = pipe(prompt=f"{j['prompt']}, {STYLE}", negative_prompt=NEG, num_inference_steps=4, guidance_scale=0,
                           width=j.get("w", 768), height=j.get("h", 1344), generator=torch.Generator().manual_seed(seed)).images[0]
            p = out / f"{j['name']}_s{seed}{'_st' + str(j.get('strength')) if j.get('init') else ''}.png"
            img.save(p)
            print(f"{p.name}: {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
