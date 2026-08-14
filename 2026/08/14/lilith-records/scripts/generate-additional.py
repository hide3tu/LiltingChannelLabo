#!/usr/bin/env python3
"""Lilith Records追加画像生成スクリプト - structured scene版"""

import json
import sys
import time
from pathlib import Path
import httpx

GENSERVER_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("/Users/hide3tu/projects/LiltingChannelLabo/2026/08/14/lilith-records/public/images")

def make_scene_spec(place: str, lighting: str, camera: str, composition: str,
                    kei: dict, kana: dict, koharu: dict, kurara: dict,
                    relations: list[str] | None = None) -> dict:
    """Build a scene_spec JSON for 4 characters."""
    def char_block(char_id: str, spec: dict) -> dict:
        return {
            "id": char_id,
            "enabled": True,
            "outfit": spec.get("outfit", "white and blue idol stage costume"),
            "position": spec.get("position", ""),
            "depth": spec.get("depth", "foreground"),
            "pose": spec.get("pose", ""),
            "action": spec.get("action", ""),
            "expression": spec.get("expression", ""),
            "gaze": spec.get("gaze", "looking at viewer"),
            "prop": spec.get("prop", ""),
            "relation": spec.get("relation", ""),
            "extra": spec.get("extra", ""),
        }
    return {
        "version": 1,
        "allow_other_people": False,
        "global": {
            "place": place,
            "weather": "",
            "time": "",
            "lighting": lighting,
            "camera": camera,
            "composition": composition,
            "spatial_layout": "",
            "style": "vivid anime idol aesthetic, masterpiece, best quality, very aesthetic",
            "extra": "",
        },
        "characters": [
            char_block("keichan", kei),
            char_block("kanachan", kana),
            char_block("koharu", koharu),
            char_block("kurara", kurara),
        ],
        "guest_characters": [],
        "relations": relations or [],
    }

IMAGES = [
    {
        "name": "live-performance.jpg",
        "dir": "events",
        "text_ja": "4人のアイドルがライブステージでパフォーマンス。けいは左でスタンドマイク、かなは中央でダンス、こはるは右でダンス、くらは奥でドラム。ネオンLED背景、スポットライト。",
        "scene_spec": make_scene_spec(
            place="idol live concert stage, neon LED backdrop, speaker stacks, pyrotechnics",
            lighting="dramatic stage spotlights, colored beam lights, pink and blue gels",
            camera="wide angle shot from audience perspective, slightly low angle",
            composition="four girls on stage in a V-formation, dynamic performance pose",
            kei={"position": "stage left", "depth": "foreground", "pose": "singing into standing mic",
                 "action": "holding mic stand, leaning forward energetically", "expression": "passionate, singing",
                 "prop": "standing microphone"},
            kana={"position": "center stage", "depth": "foreground", "pose": "arms spread wide, dancing",
                  "action": "dancing with arm choreography", "expression": "bright smile, singing",
                  "prop": "handheld microphone"},
            koharu={"position": "stage right", "depth": "foreground", "pose": "dynamic dance pose",
                    "action": "mid-choreography, one arm raised", "expression": "determined smile",
                    "prop": "handheld microphone"},
            kurara={"position": "center", "depth": "background", "pose": "standing at drum kit",
                    "action": "playing drums with drumsticks", "expression": "focused smile",
                    "prop": "drum kit, drumsticks", "outfit": "white and blue idol stage costume with rolled sleeves"},
            relations=["Kei, Kana, and Koharu perform as front line; Kurara plays drums on a raised rear riser"],
        ),
    },
    {
        "name": "behind-scenes.jpg",
        "dir": "events",
        "text_ja": "4人のアイドルが楽屋でリラックス。けいはソファで笑い、かなはドリンクを持って立ち話、こはるは床でスマホ、くらは壁にもたれて見守る。温かい照明、カジュアルな私服。",
        "scene_spec": make_scene_spec(
            place="backstage dressing room, mirrors with warm bulbs, costume rack, sofa",
            lighting="warm tungsten overhead lights, soft and natural",
            camera="medium shot, candid documentary style",
            composition="four girls relaxing together, some sitting some standing, casual group",
            kei={"position": "left", "depth": "foreground", "pose": "sitting on sofa",
                 "action": "laughing, looking at Kana", "expression": "happy laugh",
                 "gaze": "looking at Kana", "outfit": "casual oversized hoodie and shorts"},
            kana={"position": "center", "depth": "foreground", "pose": "standing, holding a drink",
                  "action": "chatting with friends", "expression": "natural smile",
                  "gaze": "looking at Kei", "outfit": "casual tank top and jeans"},
            koharu={"position": "right", "depth": "foreground", "pose": "sitting cross-legged on floor",
                    "action": "playing with phone", "expression": "gentle smile",
                    "gaze": "looking at phone", "outfit": "casual sweater and leggings"},
            kurara={"position": "center-right", "depth": "background", "pose": "leaning against wall",
                    "action": "watching the others fondly", "expression": "warm smile",
                    "gaze": "looking at others", "outfit": "casual long cardigan and skirt"},
            relations=["relaxed candid moment, no posing for camera"],
        ),
    },
    {
        "name": "debut-event.jpg",
        "dir": "events",
        "text_ja": "4人のアイドルがデビュー記者会見。一列に並んで観客に向かう。けいは手を振り、かなは花束を持ち、こはるは拍手し、くらは会釈。フォーマルな衣装、明るい照明。",
        "scene_spec": make_scene_spec(
            place="press conference room, large banner backdrop with group logo, podium",
            lighting="professional event lighting, bright and even, camera flash accents",
            camera="frontal wide shot from press area",
            composition="four girls standing in a row behind a long table, facing audience",
            kei={"position": "left", "depth": "foreground", "pose": "standing upright",
                 "action": "waving to audience with one hand", "expression": "confident smile",
                 "outfit": "formal white blazer over blue dress"},
            kana={"position": "center-left", "depth": "foreground", "pose": "standing upright",
                  "action": "holding bouquet of flowers", "expression": "excited smile",
                  "outfit": "formal white blouse and blue skirt", "prop": "bouquet of white and blue flowers"},
            koharu={"position": "center-right", "depth": "foreground", "pose": "standing upright",
                    "action": "clapping hands together", "expression": "shy happy smile",
                    "outfit": "formal white dress with blue ribbon belt"},
            kurara={"position": "right", "depth": "foreground", "pose": "standing upright",
                    "action": "bowing slightly to audience", "expression": "graceful smile",
                    "outfit": "formal white blouse and blue pencil skirt"},
            relations=["standing together as a group at their debut press conference"],
        ),
    },
    {
        "name": "promo-banner.jpg",
        "dir": "promo",
        "text_ja": "4人のアイドルがプロモーションポース。V字フォーメーションでカメラに向かう。けいは腰に手、かなは腕を広げ、こはるはピース、くらは背後で手を組む。カラフルなグラデーション背景。",
        "scene_spec": make_scene_spec(
            place="abstract colorful gradient studio, floating geometric shapes, sparkles",
            lighting="even studio lighting, bright and vivid, rim light accents",
            camera="frontal medium-wide shot, eye level",
            composition="four girls in a tight V-formation, hero pose facing camera",
            kei={"position": "center-left", "depth": "foreground", "pose": "hero pose, one hand on hip",
                 "action": "pointing forward with other hand", "expression": "determined confident smile"},
            kana={"position": "center", "depth": "foreground", "pose": "arms crossed then spreading open",
                  "action": "welcoming gesture, chest out", "expression": "bright cheerful smile"},
            koharu={"position": "center-right", "depth": "foreground", "pose": "peace sign with both hands",
                    "action": "winking", "expression": "playful wink, cute smile"},
            kurara={"position": "center", "depth": "slightly behind", "pose": "hands clasped behind back",
                    "action": "standing tall and elegant", "expression": "mysterious confident smile",
                    "outfit": "white and blue idol stage costume with cape"},
            relations=["tight promotional group shot, all facing camera directly"],
        ),
    },
]


def generate_image(name: str, text_ja: str, scene_spec: dict, output_path: Path) -> bool:
    """Generate image using structured scene compiler."""
    payload = {
        "model": "anima",
        "text_ja": text_ja,
        "structured_scene": True,
        "scene_spec_json": json.dumps(scene_spec, ensure_ascii=False),
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

        item = result["items"][0]
        image_url = item.get("image_url")

        if not image_url:
            print("✗ レスポンスにimage_urlが含まれていません")
            return False

        print(f"✓ 生成完了: {image_url}")
        print(f"  経過時間: {result.get('elapsed_s', 0):.1f}s")
        print(f"  生成prompt: {result.get('prompt_en', '')[:120]}...")

        full_url = f"{GENSERVER_URL}{image_url}"
        img_response = httpx.get(full_url, timeout=30.0)
        img_response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
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
    print("Lilith Records 追加画像生成 (structured scene)")
    print("=" * 60)

    try:
        health = httpx.get(f"{GENSERVER_URL}/api/health", timeout=5.0)
        print(f"Genserver状態: {health.json()}")
    except Exception as e:
        print(f"✗ genserverに接続できません: {e}")
        sys.exit(1)

    success_count = 0

    for img_spec in IMAGES:
        output_path = OUTPUT_DIR / img_spec["dir"] / img_spec["name"]

        if generate_image(img_spec["name"], img_spec["text_ja"], img_spec["scene_spec"], output_path):
            success_count += 1

        time.sleep(2)

    print("\n" + "=" * 60)
    print(f"生成完了: {success_count}/{len(IMAGES)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
