#!/usr/bin/env python3
"""Lilith Records集合画像生成 - 個別生成 + 合成"""

import json
import sys
import time
from pathlib import Path
import httpx
from PIL import Image
import io

GENSERVER_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("/Users/hide3tu/projects/LiltingChannelLabo/2026/08/14/lilith-records/public/images/group")

# 各キャラクターの個別生成設定
CHARACTERS = [
    {
        "id": "kei",
        "trigger": "keichan",
        "prompt": "1girl, solo, keichan, masterpiece, best quality, very aesthetic, vivid colors, "
                  "blonde hair, long hair, blue eyes, blunt bangs, hair intakes, sidelocks, "
                  "half updo, braid, blue ribbon, looking at viewer, "
                  "idol stage costume, white and blue outfit with ribbon, "
                  "hand on hip, confident pose, bright smile",
        "position": (0, 0),  # 左上
    },
    {
        "id": "kana",
        "trigger": "kanachan",
        "prompt": "1girl, solo, kanachan, masterpiece, best quality, very aesthetic, vivid colors, "
                  "brown hair, medium hair, side ponytail, ahoge, double parted bangs, blue scrunchie, "
                  "looking at viewer, "
                  "idol stage costume, white and blue outfit, "
                  "arms spread wide, welcoming pose, cheerful smile",
        "position": (1, 0),  # 右上
    },
    {
        "id": "koharu",
        "trigger": "koharu",
        "prompt": "1girl, solo, koharu, masterpiece, best quality, very aesthetic, vivid colors, "
                  "short messy black hair, blue ribbon, red eyes, "
                  "looking at viewer, "
                  "idol stage costume, white and blue outfit, "
                  "peace sign with one hand, cute pose, happy smile",
        "position": (0, 1),  # 左下
    },
    {
        "id": "kurara",
        "trigger": "kurara",
        "prompt": "1girl, solo, kurara, masterpiece, best quality, very aesthetic, vivid colors, "
                  "long rose-brown hair, center parted hair, stud earrings, light makeup, "
                  "looking at viewer, "
                  "idol stage costume, white and blue outfit with cape, "
                  "hands behind back, elegant pose, mysterious smile",
        "position": (1, 1),  # 右下
    },
]


def generate_character(char: dict) -> Image.Image | None:
    """個別キャラクター画像を生成"""
    payload = {
        "model": "anima",
        "text_ja": char["prompt"],
        "use_lora": True,
        "lora_name": "anima-4char-v1_epoch100.safetensors",
        "lora_trigger": char["trigger"],
        "lora_strength": 1.0,
        "use_speed_lora": True,
        "width": 832,
        "height": 832,
        "steps": 8,
        "cfg_scale": 1.0,
        "seed": -1,
        "count": 1,
        "include_image": False,
    }

    print(f"  生成中: {char['id']}")

    try:
        response = httpx.post(
            f"{GENSERVER_URL}/api/generate",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("ok") or not result.get("items"):
            print(f"  ✗ 失敗: {char['id']}")
            return None

        item = result["items"][0]
        image_url = item.get("image_url")

        if not image_url:
            print(f"  ✗ URLなし: {char['id']}")
            return None

        # 画像をダウンロード
        full_url = f"{GENSERVER_URL}{image_url}"
        img_response = httpx.get(full_url, timeout=30.0)
        img_response.raise_for_status()

        img = Image.open(io.BytesIO(img_response.content))
        print(f"  ✓ 完了: {char['id']}")

        return img

    except Exception as e:
        print(f"  ✗ エラー: {char['id']} - {e}")
        return None


def compose_group_image(characters: list[dict]) -> bool:
    """個別画像を2x2グリッドで合成"""
    print("\n個別キャラクター画像生成中...")

    images = {}
    for char in characters:
        img = generate_character(char)
        if img:
            images[char["id"]] = img
        time.sleep(1)

    if len(images) != 4:
        print(f"✗ {len(images)}/4人の画像しか生成できませんでした")
        return False

    # 2x2グリッドで合成（1536x768のヒーロー画像サイズに合わせる）
    canvas_width = 1536
    canvas_height = 768
    cell_width = canvas_width // 2
    cell_height = canvas_height // 2

    canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

    for char in characters:
        img = images[char["id"]]
        x, y = char["position"]
        # リサイズして配置
        img_resized = img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
        canvas.paste(img_resized, (x * cell_width, y * cell_height))

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "main.jpg"
    canvas.save(output_path, "JPEG", quality=95)
    print(f"\n✓ 集合画像保存: {output_path}")

    return True


def main():
    print("=" * 60)
    print("Lilith Records 集合画像生成（個別生成 + 合成）")
    print("=" * 60)

    try:
        health = httpx.get(f"{GENSERVER_URL}/api/health", timeout=5.0)
        print(f"Genserver状態: {health.json()}")
    except Exception as e:
        print(f"✗ genserverに接続できません: {e}")
        sys.exit(1)

    if compose_group_image(CHARACTERS):
        print("\n✓ 成功")
        return 0
    else:
        print("\n✗ 失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
