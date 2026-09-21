import json
import os
import subprocess
from pathlib import Path

import requests
from runwayml import RunwayML, TaskFailedError


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
SCENES_FILE = ROOT / "scripts" / "scenes.json"
OUTPUT_DIR = ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Run shell command
# ---------------------------------------------------------
def run_command(command):
    print("Running:", " ".join(str(x) for x in command))
    subprocess.run(command, check=True)


# ---------------------------------------------------------
# Download generated Runway video
# ---------------------------------------------------------
def download_video(url, output_path):
    print("Downloading AI video...")

    response = requests.get(url, timeout=300)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"Downloaded: {output_path}")


# ---------------------------------------------------------
# Generate narration using eSpeak
# ---------------------------------------------------------
def generate_voice(text, output_path):
    print("Generating narration...")

    run_command(
        [
            "espeak-ng",
            "-v",
            "en-us",
            "-s",
            "145",
            "-p",
            "55",
            "-w",
            str(output_path),
            text,
        ]
    )


# ---------------------------------------------------------
# Generate AI scene using Runway Gen-4.5
# ---------------------------------------------------------
def generate_scene(client, scene, index):
    title = scene.get("title", f"Scene {index}")

    print()
    print("=" * 60)
    print(f"Generating scene {index}: {title}")
    print("=" * 60)

    prompt = scene["prompt"]

    try:
        task = client.image_to_video.create(
            model=scene.get("model", "gen4.5"),
            prompt_text=prompt,
            ratio=scene.get("ratio", "1280:720"),
            duration=int(scene.get("duration", 5)),
        ).wait_for_task_output()

    except TaskFailedError as error:
        print("Runway generation failed.")

        try:
            print(error.task_details)
        except Exception:
            print(error)

        raise

    if not task.output:
        raise RuntimeError("Runway returned no video output.")

    video_url = task.output[0]

    raw_video = OUTPUT_DIR / f"scene_{index:02d}_ai.mp4"

    download_video(video_url, raw_video)

    return raw_video


# ---------------------------------------------------------
# Combine AI video + narration
# ---------------------------------------------------------
def add_narration(video_path, narration_text, index):
    voice_path = OUTPUT_DIR / f"scene_{index:02d}_voice.wav"

    final_scene = OUTPUT_DIR / f"scene_{index:02d}_final.mp4"

    generate_voice(narration_text, voice_path)

    print("Combining AI video and narration...")

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(voice_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(final_scene),
        ]
    )

    return final_scene


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    print()
    print("==============================================")
    print(" SharvinKidsTV V3 - AI Video Generator")
    print("==============================================")
    print()

    api_key = os.getenv("RUNWAYML_API_SECRET")

    if not api_key:
        raise RuntimeError(
            "RUNWAYML_API_SECRET is missing. "
            "Add it in GitHub Settings -> Secrets and variables -> Actions."
        )

    if not SCENES_FILE.exists():
        raise FileNotFoundError(
            f"Scenes file not found: {SCENES_FILE}"
        )

    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    if not scenes:
        raise RuntimeError("scenes.json contains no scenes.")

    print(f"Found {len(scenes)} scene(s).")

    client = RunwayML(api_key=api_key)

    completed_scenes = []

    for index, scene in enumerate(scenes, start=1):

        raw_video = generate_scene(
            client,
            scene,
            index
        )

        narration = scene.get("narration", "")

        if narration.strip():

            final_scene = add_narration(
                raw_video,
                narration,
                index
            )

        else:
            final_scene = raw_video

        completed_scenes.append(final_scene)

    # -----------------------------------------------------
    # For our V3 test we currently have ONE scene.
    # Copy it to the expected GitHub artifact filename.
    # -----------------------------------------------------

    final_output = (
        OUTPUT_DIR /
        "sharvinkidstv-v3-test-a-for-apple.mp4"
    )

    if len(completed_scenes) == 1:

        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(completed_scenes[0]),
                "-c",
                "copy",
                str(final_output),
            ]
        )

    else:

        concat_file = OUTPUT_DIR / "concat.txt"

        with open(concat_file, "w", encoding="utf-8") as f:

            for scene in completed_scenes:
                f.write(
                    f"file '{scene.resolve()}'\n"
                )

        run_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(final_output),
            ]
        )

    print()
    print("==============================================")
    print("SUCCESS!")
    print("==============================================")
    print()
    print(f"Final video: {final_output}")
    print()


if __name__ == "__main__":
    main()
