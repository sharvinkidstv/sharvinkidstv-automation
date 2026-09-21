import json
import os
import subprocess
from pathlib import Path

import requests
from runwayml import RunwayML, TaskFailedError


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SCENES_FILE = ROOT / "scripts" / "scenes.json"
OUTPUT_DIR = ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# RUN COMMAND
# ============================================================

def run_command(command):
    print("Running:", " ".join(str(x) for x in command))

    subprocess.run(
        command,
        check=True
    )


# ============================================================
# DOWNLOAD RUNWAY VIDEO
# ============================================================

def download_video(url, output_path):

    print("Downloading AI video...")

    response = requests.get(
        url,
        timeout=300
    )

    response.raise_for_status()

    with open(output_path, "wb") as file:
        file.write(response.content)

    print(f"Downloaded: {output_path}")


# ============================================================
# GENERATE VOICE
# ============================================================

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
            text
        ]
    )


# ============================================================
# GENERATE AI VIDEO SCENE
# ============================================================

def generate_scene(client, scene, index):

    title = scene.get(
        "title",
        f"Scene {index}"
    )

    print()
    print("=" * 70)
    print(f"GENERATING SCENE {index}: {title}")
    print("=" * 70)

    prompt = scene["prompt"]

    print("Prompt:")
    print(prompt)
    print()

    try:

        task = client.image_to_video.create(
            model=scene.get(
                "model",
                "gen4.5"
            ),
            prompt_text=prompt,
            ratio=scene.get(
                "ratio",
                "1280:720"
            ),
            duration=int(
                scene.get(
                    "duration",
                    5
                )
            )
        ).wait_for_task_output()

    except TaskFailedError as error:

        print()
        print("RUNWAY GENERATION FAILED")
        print()

        try:
            print(error.task_details)
        except Exception:
            print(error)

        raise

    if not task.output:

        raise RuntimeError(
            "Runway returned no video output."
        )

    video_url = task.output[0]

    raw_video = (
        OUTPUT_DIR /
        f"scene_{index:02d}_ai.mp4"
    )

    download_video(
        video_url,
        raw_video
    )

    return raw_video


# ============================================================
# ADD NARRATION
# ============================================================

def add_narration(
    video_path,
    narration_text,
    index
):

    voice_path = (
        OUTPUT_DIR /
        f"scene_{index:02d}_voice.wav"
    )

    final_scene = (
        OUTPUT_DIR /
        f"scene_{index:02d}_final.mp4"
    )

    generate_voice(
        narration_text,
        voice_path
    )

    print("Combining AI video + narration...")

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

            str(final_scene)
        ]
    )

    return final_scene


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_final_video(
    completed_scenes,
    final_output
):

    print()
    print("=" * 70)
    print("CREATING FINAL VIDEO")
    print("=" * 70)

    # --------------------------------------------------------
    # ONE SCENE
    # --------------------------------------------------------

    if len(completed_scenes) == 1:

        run_command(
            [
                "ffmpeg",
                "-y",

                "-i",
                str(completed_scenes[0]),

                "-c",
                "copy",

                str(final_output)
            ]
        )

        return

    # --------------------------------------------------------
    # MULTIPLE SCENES
    # --------------------------------------------------------

    concat_file = (
        OUTPUT_DIR /
        "concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for scene in completed_scenes:

            file.write(
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

            str(final_output)
        ]
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("       SHARVINKIDSTV V3 AI VIDEO GENERATOR")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # CHECK API KEY
    # --------------------------------------------------------

    api_key = os.getenv(
        "RUNWAYML_API_SECRET"
    )

    if not api_key:

        raise RuntimeError(
            "RUNWAYML_API_SECRET is missing.\n"
            "Go to GitHub:\n"
            "Settings -> Secrets and variables -> Actions\n"
            "and create the repository secret."
        )

    print("Runway API key detected.")
    print()

    # --------------------------------------------------------
    # CHECK SCENES FILE
    # --------------------------------------------------------

    if not SCENES_FILE.exists():

        raise FileNotFoundError(
            f"Scenes file not found: {SCENES_FILE}"
        )

    # --------------------------------------------------------
    # READ JSON
    # --------------------------------------------------------

    with open(
        SCENES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    # IMPORTANT:
    # scenes.json contains:
    #
    # {
    #   "scenes": [
    #      ...
    #   ]
    # }
    #

    scenes = data["scenes"]

    if not scenes:

        raise RuntimeError(
            "scenes.json contains no scenes."
        )

    print(
        f"Found {len(scenes)} scene(s)."
    )

    # --------------------------------------------------------
    # CONNECT TO RUNWAY
    # --------------------------------------------------------

    client = RunwayML(
        api_key=api_key
    )

    completed_scenes = []

    # --------------------------------------------------------
    # PROCESS EACH SCENE
    # --------------------------------------------------------

    for index, scene in enumerate(
        scenes,
        start=1
    ):

        # Generate AI video
        raw_video = generate_scene(
            client,
            scene,
            index
        )

        # Add narration
        narration = scene.get(
            "narration",
            ""
        )

        if narration.strip():

            final_scene = add_narration(
                raw_video,
                narration,
                index
            )

        else:

            final_scene = raw_video

        completed_scenes.append(
            final_scene
        )

    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------

    final_output = (
        OUTPUT_DIR /
        "sharvinkidstv-v3-test-a-for-apple.mp4"
    )

    create_final_video(
        completed_scenes,
        final_output
    )

    print()
    print("=" * 70)
    print("                 SUCCESS!")
    print("=" * 70)
    print()
    print(
        f"Final video created:"
    )
    print(final_output)
    print()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
