import sys
import torch
from diffusers import QwenImage21Pipeline, TaylorSeerCacheConfig

WORKAROUND = "--workaround" in sys.argv
device = "cuda" if torch.cuda.is_available() else "mps"

if WORKAROUND:
    import diffusers.hooks.taylorseer_cache as ts

    _orig_update = ts.TaylorSeerState.update

    def _update(self, outputs):
        # With the KV cache, step 0 (prefill) returns prefix+target tokens and later steps return
        # target tokens only. Drop the stale factors when the shape changes.
        if not self.is_inactive and self.last_update_step is not None:
            for i, feat in enumerate(outputs):
                prev = self.taylor_factors.get(i, {}).get(0)
                if prev is not None and prev.shape != feat.shape:
                    self.taylor_factors = {}
                    self.last_update_step = None
                    break
        return _orig_update(self, outputs)

    ts.TaylorSeerState.update = _update

pipe = QwenImage21Pipeline.from_pretrained("Qwen/Qwen-Image-2.1", torch_dtype=torch.bfloat16).to(device)
pipe.transformer.enable_cache(
    TaylorSeerCacheConfig(cache_interval=3, disable_cache_before_step=3, max_order=1, use_lite_mode=True)
)
image = pipe(
    prompt="a cat sitting on a wall",
    width=512,
    height=512,
    num_inference_steps=8,
    true_cfg_scale=1.0,
    generator=torch.Generator("cpu").manual_seed(0),
).images[0]  # use_kv_cache defaults to True
image.save("out-workaround.png" if WORKAROUND else "out.png")
print("OK")
