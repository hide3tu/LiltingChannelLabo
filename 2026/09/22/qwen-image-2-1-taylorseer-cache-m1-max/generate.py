"""Qwen-Image 2.1 on Diffusers with the TaylorSeer cache, keeping the default KV cache on.

Diffusers (as of commit 80c7ed26) crashes on the second step when TaylorSeer and the KV cache are
both enabled (https://github.com/huggingface/diffusers/issues/14829). The patch below restarts the
Taylor expansion when the hooked module's output shape changes, which is what happens between the
KV-cache prefill step (prefix + target tokens) and the following steps (target tokens only).
"""
import argparse
import time
from pathlib import Path

import torch
from diffusers import QwenImage21Pipeline, TaylorSeerCacheConfig
from PIL import Image

import diffusers.hooks.taylorseer_cache as ts

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="./model", help="local dir or Qwen/Qwen-Image-2.1")
parser.add_argument("--prompt-file", type=Path, required=True)
parser.add_argument("--image", type=Path, action="append", default=[], help="reference image(s) for editing")
parser.add_argument("--out", type=Path, default=Path("out.png"))
parser.add_argument("--width", type=int, default=832)
parser.add_argument("--height", type=int, default=1216)
parser.add_argument("--steps", type=int, default=40)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--cache-interval", type=int, default=3, help="0 disables TaylorSeer")
parser.add_argument("--output-resolution", type=int, help="see the edit article: 1006 keeps 832x1216 references unscaled")
args = parser.parse_args()

_orig_update = ts.TaylorSeerState.update


def _update(self, outputs):
    if not self.is_inactive and self.last_update_step is not None:
        for i, feat in enumerate(outputs):
            prev = self.taylor_factors.get(i, {}).get(0)
            if prev is not None and prev.shape != feat.shape:
                self.taylor_factors = {}
                self.last_update_step = None
                break
    return _orig_update(self, outputs)


ts.TaylorSeerState.update = _update

device = "cuda" if torch.cuda.is_available() else "mps"
pipe = QwenImage21Pipeline.from_pretrained(args.model, torch_dtype=torch.bfloat16).to(device)
if args.cache_interval > 0:
    pipe.transformer.enable_cache(
        TaylorSeerCacheConfig(
            cache_interval=args.cache_interval,
            disable_cache_before_step=3,  # keep >= 2 with the KV cache: step 0 is the prefill step
            max_order=1,
            taylor_factors_dtype=torch.float32,
            use_lite_mode=True,
        )
    )

inputs = dict(
    prompt=args.prompt_file.read_text(),
    width=args.width,
    height=args.height,
    num_inference_steps=args.steps,
    true_cfg_scale=1.0,
    generator=torch.Generator("cpu").manual_seed(args.seed),
)
if args.image:
    inputs["image"] = [Image.open(p).convert("RGB") for p in args.image]
if args.output_resolution:
    inputs["output_resolution"] = args.output_resolution

start = time.perf_counter()
with torch.inference_mode():
    image = pipe(**inputs).images[0]
if device == "mps":
    torch.mps.synchronize()
print(f"generation: {time.perf_counter() - start:.1f}s")
image.save(args.out)
