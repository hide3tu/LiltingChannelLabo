#!/usr/bin/env python3
"""Lilith Records集合画像 - 個別生成 + 合成（確実な4人）"""

import json
import sys
import time
from pathlib import Path
import httpx
from PIL import Image, ImageDraw
import io

GENSERVER_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("/Users/hide3tu/projects/LiltingChannelLabo/2026/08/14/lilith-records/public/images/group")

# 4人を個別生成
CHARACTERS = [
    {
        "id": "kei",
        "trigger": "keichan",
        "prompt": "1girl, solo, keichan, masterpiece, best quality, very aesthetic, vivid colors, "
                  "blonde long hair, blue eyes, blunt bangs, hair intakes, sidelocks, blue ribbon, "
                  "idol stage costume, white and blue outfit with ribbon, "
                  "hand on hip, confident pose, bright smile, looking at viewer, "
                  "transparent background, simple background, white background",
        "x_pos": 0,  # 左
    },
    {
        "id": "kana",
        "trigger": "kanachan",
        "prompt": "1girl, solo, kanachan, masterpiece, best quality, very aesthetic, vivid colors, "
                  "brown shoulder-length hair, short side ponytail, ahoge, double parted bangs, blue scrunchie, "
                  "idol stage costume, white and blue outfit, "
                  "arms spread wide, welcoming pose, cheerful smile, looking at viewer, "
                  "transparent background, simple background, white background",
        "x_pos": 1,  # 中央左
    },
    {
        "id": "koharu",
        "trigger": "koharu",
        "prompt": "1girl, solo, koharu, masterpiece, best quality, very aesthetic, vivid colors, "
                  "short messy black hair, blue ribbon, red eyes, "
                  "idol stage costume, white and blue outfit, "
                  "peace sign with one hand, cute pose, happy smile, looking at viewer, "
                  "transparent background, simple background, white background",
        "x_pos": 2,  # 中央右
    },
    {
        "id": "kurara",
        "trigger": "kurara",
        "prompt": "1girl, solo, kurara, masterpiece, best quality, very aesthetic, vivid colors, "
                  "long rose-brown hair, center parted, stud earrings, light makeup, "
                  "idol stage costume, white and blue outfit with small cape, "
                  "hands behind back, elegant pose, mysterious smile, looking at viewer, "
                  "transparent background, simple background, white background",
        "x_pos": 3,  # 右
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
        "width": 768,
        "height": 1024,
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


def remove_background(img: Image.Image) -> Image.Image:
    """白背景を透明化（簡易版）"""
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    
    for item in data:
        # 白に近い色を透明化
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    return img


def compose_group_image(characters: list[dict]) -> bool:
    """個別画像を並べて合成"""
    print("\n=== 個別キャラクター画像生成 ===")

    images = {}
    for char in characters:
        img = generate_character(char)
        if img:
            images[char["id"]] = img
        time.sleep(1)

    if len(images) != 4:
        print(f"\n✗ {len(images)}/4人の画像しか生成できませんでした")
        return False

    # 1536x864のキャンバス（16:9）
    canvas_width = 1536
    canvas_height = 864
    
    # 背景をグラデーション（アイドルステージ風）
    canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # 簡単なグラデーション背景
    for y in range(canvas_height):
        ratio = y / canvas_height
        r = int(255 * (1 - ratio) + 200 * ratio)
        g = int(255 * (1 - ratio) + 220 * ratio)
        b = int(255 * (1 - ratio) + 255 * ratio)
        draw.line([(0, y), (canvas_width, y)], fill=(r, g, b))

    # 各キャラクターを配置（横一列）
    char_width = canvas_width // 4
    char_height = int(canvas_height * 0.9)
    
    for char in characters:
        img = images[char["id"]]
        # リサイズ（アスペクト比維持）
        img_ratio = img.width / img.height
        target_ratio = char_width / char_height
        
        if img_ratio > target_ratio:
            # 幅に合わせる
            new_width = char_width
            new_height = int(char_width / img_ratio)
        else:
            # 高さに合わせる
            new_height = char_height
            new_width = int(char_height * img_ratio)
        
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 背景除去
        img_rgba = remove_background(img_resized)
        
        # 配置位置
        x_offset = char["x_pos"] * char_width + (char_width - new_width) // 2
        y_offset = canvas_height - new_height - 20  # 下揃え
        
        # 合成
        canvas.paste(img_rgba, (x_offset, y_offset), img_rgba)

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "main.jpg"
    canvas.save(output_path, "JPEG", quality=95)
    print(f"\n✓ 集合画像保存: {output_path}")

    return True


def main():
    print("=" * 60)
    print("Lilith Records 集合画像（個別生成 + 合成）")
    print("=" * 60)

    try:
        health = httpx.get(f"{GENSERVER_URL}/api/health", timeout=5.0)
        print(f"Genserver状態: {health.json()}")
    except Exception as e:
        print(f"✗ genserverに接続できません: {e}")
        sys.exit(1)

    if compose_group_image(CHARACTERS):
        print("\n✓ 成功：4人全員が確実に描かれています")
        return 0
    else:
        print("\n✗ 失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
