#!/usr/bin/env python3
"""Lilith Records追加画像生成スクリプト（修正版）"""

import sys
import time
from pathlib import Path
import httpx

GENSERVER_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("/Users/hide3tu/projects/LiltingChannelLabo/2026/08/14/lilith-records/public/images")

# 生成する画像のリスト
IMAGES = [
    {
        "name": "live-performance.jpg",
        "prompt": "4girls, masterpiece, best quality, very aesthetic, vivid colors, idol live concert, stage performance, keichan kanachan koharu kurara, singing, dancing, spotlights, crowd, energetic atmosphere, concert photography",
        "dir": "events"
    },
    {
        "name": "behind-scenes.jpg",
        "prompt": "4girls, masterpiece, best quality, very aesthetic, vivid colors, idol backstage, keichan kanachan koharu kurara, casual clothes, relaxed atmosphere, candid moment, documentary style photography",
        "dir": "events"
    },
    {
        "name": "debut-event.jpg",
        "prompt": "4girls, masterpiece, best quality, very aesthetic, vivid colors, idol debut event, keichan kanachan koharu kurara, press conference, microphone, announcement, professional event photography",
        "dir": "events"
    },
    {
        "name": "promo-banner.jpg",
        "prompt": "4girls, masterpiece, best quality, very aesthetic, vivid colors, idol promotional poster, keichan kanachan koharu kurara, colorful gradient background, eye-catching design, marketing material, text overlay",
        "dir": "promo"
    },
]

def generate_image(name: str, prompt: str, output_path: Path) -> bool:
    """画像を生成して保存"""
    
    payload = {
        "model": "anima",
        "text_ja": prompt,
        "use_lora": True,
        "lora_name": "anima-4char-v1_epoch100.safetensors",
        "lora_trigger": "keichan,kanachan,koharu,kurara",
        "lora_strength": 1.0,
        "use_speed_lora": True,
        "width": 1024,
        "height": 1024,
        "steps": 8,
        "cfg_scale": 1.0,
        "seed": -1,
        "count": 1,
        "include_image": False,
    }
    
    print(f"\n生成中: {name}")
    print(f"プロンプト: {prompt[:80]}...")
    
    try:
        response = httpx.post(
            f"{GENSERVER_URL}/api/generate",
            json=payload,
            timeout=180.0,
        )
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            print(f"✗ 生成失敗: {result}")
            return False
        
        if not result.get("items"):
            print("✗ レスポンスにitemsが含まれていません")
            return False
        
        # 画像URLを取得
        item = result["items"][0]
        image_url = item.get("image_url")
        
        if not image_url:
            print("✗ レスポンスにimage_urlが含まれていません")
            return False
        
        print(f"✓ 生成完了: {image_url}")
        print(f"  経過時間: {result.get('elapsed_s', 0):.1f}s")
        
        # 画像をダウンロード
        full_url = f"{GENSERVER_URL}{image_url}"
        img_response = httpx.get(full_url, timeout=30.0)
        img_response.raise_for_status()
        
        # ディレクトリ作成
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存
        output_path.write_bytes(img_response.content)
        print(f"✓ 保存完了: {output_path}")
        
        return True
        
    except httpx.TimeoutException:
        print("✗ リクエストがタイムアウトしました")
        return False
    except httpx.HTTPError as e:
        print(f"✗ HTTPエラー: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  レスポンス: {e.response.text}")
        return False
    except Exception as e:
        print(f"✗ エラー: {e}")
        return False

def main():
    print("=" * 60)
    print("Lilith Records 追加画像生成")
    print("=" * 60)
    
    # genserverの接続確認
    try:
        health = httpx.get(f"{GENSERVER_URL}/api/health", timeout=5.0)
        print(f"Genserver状態: {health.json()}")
    except Exception as e:
        print(f"✗ genserverに接続できません: {e}")
        sys.exit(1)
    
    success_count = 0
    
    for img_spec in IMAGES:
        output_path = OUTPUT_DIR / img_spec["dir"] / img_spec["name"]
        
        if generate_image(img_spec["name"], img_spec["prompt"], output_path):
            success_count += 1
        
        # 次の生成まで少し待つ
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print(f"生成完了: {success_count}/{len(IMAGES)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
