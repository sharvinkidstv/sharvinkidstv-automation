import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from runwayml import RunwayML, TaskFailedError

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

SCENES_FILE = ROOT / "scripts" / "scenes.json"


def run(cmd):
    print("$", " ".join(map(str, cmd)))
    subprocess.run([str(x) for x in cmd], check=True)


def generate_scene(client, scene, index):
    print(f"\n=== Generating scene {index}: {scene['title']} ===")
    task = client.image_to_video.create(
        model=scene.get("model", "gen4.5"),
        prompt_text=scene["prompt"],
        ratio=scene.get("ratio", "1280:720"),
        duration=int(scene.get("duration", 5)),
    )

    try:
        result = task.wait_for_task_output()
    except TaskFailedError as exc:
        print("Runway task failed.")
        print(exc.task_details)
        raise

    if not result.output:
        raise RuntimeError("Runway returned no output URL.")

    url = result.output[0]
    raw = OUTPUT / f"scene_{index:02d}_ai.mp4"

    print("Downloading generated video...")
    response = requests.get(url, timeout=180)
    response.raise_for_status()
    raw.write_bytes(response.content)
    print(f"Saved {raw}")

    return raw


def add_narration_and_music(input_video, narration, index):
    voice = OUTPUT / f"voice_{index:02d}.wav"
    final = OUTPUT / f"scene_{index:02d}_final.mp4"

    # Free local narration using eSpeak-NG.
    run([
        "espeak-ng",
        "-s", "145",
        "-p", "65",
        "-v", "en",
        "-w", voice,
        narration,
    ])

    # Keep narration clearly audible. The generated AI video remains the main visual.
    run([
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", voice,
        "-filter_complex",
        "[1:a]volume=1.0[narr];"
        "[narr]apad[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        final,
    ])

    return final


def main():
    api_key = os.environ.get("RUNWAYML_API_SECRET")
    if not api_key:
        raise SystemExit(
            "Missing RUNWAYML_API_SECRET. Add it under GitHub Settings > Secrets and variables > Actions."
        )

    data = json.loads(SCENES_FILE.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    client = RunwayML(api_key=api_key)

    final_files = []

    for i, scene in enumerate(scenes, 1):
        raw = generate_scene(client, scene, i)
        final_files.append(
            add_narration_and_music(raw, scene["narration"], i)
        )

    # For V3.1 we intentionally keep the first test as one scene.
    # If multiple scenes are later enabled, concatenate them automatically.
    if len(final_files) == 1:
        final = OUTPUT / "sharvinkidstv-v3-test-a-for-apple.mp4"
        final.write_bytes(final_files[0].read_bytes())
    else:
        concat = OUTPUT / "concat.txt"
        concat.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in final_files) + "\n",
            encoding="utf-8",
        )
        final = OUTPUT / "sharvinkidstv-v3.mp4"
        run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat,
            "-c", "copy",
            final,
        ])

    print(f"\nV3 COMPLETE: {final}")


if __name__ == "__main__":
    main()
