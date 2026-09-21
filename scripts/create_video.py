import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
FRAMES = OUTPUT / "frames"

OUTPUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)


def get_font(size, bold=False):
    if bold:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]
    else:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def run(command):
    subprocess.run(command, check=True)


def create_scene(index, scene):
    width = 1280
    height = 720

    image = Image.new("RGB", (width, height), (120, 210, 255))
    draw = ImageDraw.Draw(image)

    # Sky
    for y in range(height):
        ratio = y / height

        r = int(110 + 80 * ratio)
        g = int(200 + 30 * ratio)
        b = int(255 - 10 * ratio)

        draw.line(
            [(0, y), (width, y)],
            fill=(r, g, b)
        )

    # Clouds
    for x, y in [(120, 90), (900, 100), (570, 70)]:
        for dx, dy, radius in [
            (0, 20, 35),
            (40, 0, 45),
            (80, 20, 32)
        ]:
            draw.ellipse(
                (
                    x + dx - radius,
                    y + dy - radius,
                    x + dx + radius,
                    y + dy + radius
                ),
                fill="white"
            )

    # Grass
    draw.rectangle(
        (0, 520, width, height),
        fill=(80, 185, 90)
    )

    # Rainbow
    center_x = 640
    center_y = 520

    rainbow = [
        (300, (235, 80, 80)),
        (270, (255, 170, 50)),
        (240, (255, 230, 60)),
        (210, (80, 190, 100)),
        (180, (70, 150, 235)),
        (150, (145, 90, 210))
    ]

    for radius, color in rainbow:
        draw.arc(
            (
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius
            ),
            200,
            340,
            fill=color,
            width=18
        )

    # Main letter box
    draw.rounded_rectangle(
        (80, 150, 440, 490),
        radius=55,
        fill=(255, 247, 190),
        outline=(255, 180, 60),
        width=8
    )

    big_font = get_font(220, True)

    letter = scene["letter"]

    bbox = draw.textbbox(
        (0, 0),
        letter,
        font=big_font
    )

    text_width = bbox[2] - bbox[0]

    draw.text(
        (260 - text_width / 2, 180),
        letter,
        font=big_font,
        fill=(230, 70, 100),
        stroke_width=5,
        stroke_fill="white"
    )

    # Word
    word_font = get_font(58, True)
    line_font = get_font(38, True)

    draw.text(
        (510, 190),
        scene["word"],
        font=word_font,
        fill=(35, 70, 130)
    )

    draw.text(
        (510, 290),
        scene["line"],
        font=line_font,
        fill=(45, 60, 90)
    )

    # Balloons
    balloons = [
        (1030, 290, (245, 90, 120)),
        (1130, 360, (90, 170, 245)),
        (1000, 390, (255, 190, 60))
    ]

    for x, y, color in balloons:
        draw.ellipse(
            (x - 35, y - 45, x + 35, y + 45),
            fill=color,
            outline="white",
            width=4
        )

        draw.line(
            (x, y + 45, x - 10, y + 130),
            fill="white",
            width=3
        )

    # Channel name
    brand_font = get_font(32, True)

    draw.rounded_rectangle(
        (30, 30, 370, 90),
        radius=20,
        fill="white"
    )

    draw.text(
        (50, 45),
        "SharvinKidsTV",
        font=brand_font,
        fill=(220, 55, 95)
    )

    file_path = FRAMES / f"scene_{index:02d}.png"

    image.save(file_path)

    return file_path


def create_voice(text, output_file):
    run([
        "espeak-ng",
        "-s",
        "145",
        "-p",
        "65",
        "-v",
        "en",
        "-w",
        str(output_file),
        text
    ])


def main():

    if len(sys.argv) > 1:
        script_file = Path(sys.argv[1])
    else:
        script_file = ROOT / "scripts" / "abc-song.json"

    data = json.loads(
        script_file.read_text(encoding="utf-8")
    )

    clips = []

    for index, scene in enumerate(
        data["scenes"],
        start=1
    ):

        print(
            f"Creating scene {index}: "
            f"{scene['letter']} - {scene['word']}"
        )

        image_file = create_scene(
            index,
            scene
        )

        voice_file = OUTPUT / f"voice_{index:02d}.wav"

        create_voice(
            scene["line"],
            voice_file
        )

        clip_file = OUTPUT / f"clip_{index:02d}.mp4"

        run([
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_file),
            "-i",
            str(voice_file),
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(clip_file)
        ])

        clips.append(clip_file)

    concat_file = OUTPUT / "concat.txt"

    with concat_file.open("w", encoding="utf-8") as file:

        for clip in clips:
            file.write(
                f"file '{clip.resolve()}'\n"
            )

    final_video = OUTPUT / "sharvinkidstv-abc-song.mp4"

    run([
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
        str(final_video)
    ])

    metadata_file = OUTPUT / "metadata.json"

    metadata_file.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

    print("")
    print("====================================")
    print("SharvinKidsTV video created!")
    print("====================================")
    print(final_video)


if __name__ == "__main__":
    main()
