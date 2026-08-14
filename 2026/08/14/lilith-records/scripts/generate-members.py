#!/usr/bin/env python3
"""Generate Lilith-4 member portraits via genserver API."""

import json
import sys
import time
from pathlib import Path

import httpx

GENSERVER_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("/Users/hide3tu/projects/LiltingChannelLabo/2026/08/14/lilith-records/public/images/artists")

# Member definitions matching genserver's character presets
MEMBERS = {
    "kei": {
        "name": "Kei",
        "trigger": "keichan",
        "lora": "anima-4char-v1_epoch100.safetensors",
        "prompt": "1girl, solo, keichan, masterpiece, best quality, very aesthetic, vivid colors, "
                  "blonde hair, long hair, blue eyes, blunt bangs, hair intakes, sidelocks, "
                  "half updo, braid, blue ribbon, looking at viewer, simple background, "
                  "white background, portrait, upper body, idol outfit, white and blue costume",
    },
    "kana": {
        "name": "Kana",
        "trigger": "kanachan",
        "lora": "anima-4char-v1_epoch100.safetensors",
        "prompt": "1girl, solo, kanachan, masterpiece, best quality, very aesthetic, vivid colors, "
                  "brown hair, medium hair, side ponytail, ahoge, double parted bangs, blue scrunchie, "
                  "looking at viewer, simple background, white background, portrait, upper body, "
                  "idol outfit, white and blue costume",
    },
    "koharu": {
        "name": "Koharu",
        "trigger": "koharu",
        "lora": "anima-4char-v1_epoch100.safetensors",
        "prompt": "1girl, solo, koharu, masterpiece, best quality, very aesthetic, vivid colors, "
                  "short messy black hair, blue ribbon, red eyes, "
                  "looking at viewer, simple background, white background, portrait, upper body, "
                  "idol outfit, white and blue costume",
    },
    "kurara": {
        "name": "Kurara",
        "trigger": "kurara",
        "lora": "anima-4char-v1_epoch100.safetensors",
        "prompt": "1girl, solo, kurara, masterpiece, best quality, very aesthetic, vivid colors, "
                  "long rose-brown hair, center parted hair, stud earrings, light makeup, "
                  "looking at viewer, simple background, white background, portrait, upper body, "
                  "idol outfit, white and blue costume",
    },
}


def generate_member(member_key: str, member_data: dict) -> bool:
    """Generate a single member portrait."""
    print(f"\n{'='*60}")
    print(f"Generating: {member_data['name']}")
    print(f"{'='*60}")
    
    payload = {
        "model": "anima",
        "text_ja": member_data["prompt"],
        "use_lora": True,
        "lora_name": member_data["lora"],
        "lora_trigger": member_data["trigger"],
        "lora_strength": 1.0,
        "use_speed_lora": True,
        "width": 832,
        "height": 1216,
        "steps": 8,
        "cfg_scale": 1.0,
        "seed": -1,
        "count": 1,
        "include_image": False,  # We'll download from URL
    }
    
    try:
        response = httpx.post(
            f"{GENSERVER_URL}/api/generate",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            print(f"ERROR: Generation failed: {result}")
            return False
        
        if not result.get("items"):
            print("ERROR: No items in response")
            return False
        
        # Get the image URL
        item = result["items"][0]
        image_url = item.get("image_url")
        
        if not image_url:
            print("ERROR: No image_url in response")
            return False
        
        print(f"Generated: {image_url}")
        print(f"Prompt (EN): {result.get('prompt_en', 'N/A')[:100]}...")
        print(f"Elapsed: {result.get('elapsed_s', 0):.1f}s")
        
        # Download and save the image
        full_url = f"{GENSERVER_URL}{image_url}"
        img_response = httpx.get(full_url, timeout=30.0)
        img_response.raise_for_status()
        
        # Save to output directory
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"{member_key}.jpg"
        output_path.write_bytes(img_response.content)
        
        print(f"Saved: {output_path}")
        return True
        
    except httpx.TimeoutException:
        print("ERROR: Request timed out")
        return False
    except httpx.HTTPError as e:
        print(f"ERROR: HTTP error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Generate all member portraits."""
    print("Lilith-4 Member Portrait Generator")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Check genserver health
    try:
        health = httpx.get(f"{GENSERVER_URL}/api/health", timeout=5.0)
        print(f"Genserver status: {health.json()}")
    except Exception as e:
        print(f"ERROR: Cannot connect to genserver: {e}")
        sys.exit(1)
    
    # Generate each member
    results = {}
    for key, data in MEMBERS.items():
        results[key] = generate_member(key, data)
        time.sleep(1)  # Small delay between requests
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    for key, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {MEMBERS[key]['name']}")
    
    all_success = all(results.values())
    if all_success:
        print("\nAll portraits generated successfully!")
    else:
        print("\nSome portraits failed. Check the output above.")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
