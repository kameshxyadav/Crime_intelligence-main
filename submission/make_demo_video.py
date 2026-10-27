#!/usr/bin/env python3
"""
Builds the hackathon demo video (no voice-over, captioned) from real screenshots of the running app.

1. Starts the backend (SAMPLE_MODE=true, so no Zetaris/Nightshift/credentials are needed) and the Vite
   frontend, unless they are already listening.
2. Drives the UI with Playwright (system Chrome) and saves screenshots to submission/video_assets/shots.
3. Stitches title card, captioned screenshots and an end card into submission/demo_video.mp4 using
   imageio-ffmpeg (a bundled ffmpeg), so nothing has to be installed system-wide.

Setup:  pip install playwright imageio imageio-ffmpeg pillow numpy
Run:    python submission/make_demo_video.py            (add --no-capture to rebuild from existing shots)

The investigation scenes run in SAMPLE MODE and the video says so on screen.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "submission" / "video_assets"
SHOTS = ASSETS / "shots"
OUT = ROOT / "submission" / "demo_video.mp4"
W, H, FPS = 1920, 1080, 24
NAVY, AMBER, WHITE = (15, 27, 51), (242, 169, 59), (255, 255, 255)
APP = "http://127.0.0.1:5173"


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for(port: int, secs: int = 60) -> None:
    end = time.time() + secs
    while time.time() < end:
        if port_open(port):
            return
        time.sleep(0.5)
    raise RuntimeError(f"port {port} did not open")


def start_servers() -> list[subprocess.Popen]:
    procs = []
    if not port_open(8000):
        env = {**os.environ, "SAMPLE_MODE": "true"}
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
            cwd=ROOT / "backend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    if not port_open(5173):
        procs.append(subprocess.Popen(
            ["npx", "vite", "--port", "5173", "--host", "127.0.0.1"],
            cwd=ROOT / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    wait_for(8000)
    wait_for(5173)
    return procs


# (file, caption, seconds)
SCENES: list[tuple[str, str, float]] = []


def shot(page, name: str, caption: str, secs: float = 5.0) -> None:
    page.wait_for_timeout(900)
    page.screenshot(path=str(SHOTS / f"{name}.png"))
    SCENES.append((name, caption, secs))


def capture() -> None:
    from playwright.sync_api import sync_playwright

    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto(APP)
        page.wait_for_timeout(1500)
        shot(page, "01_login", "Four demo roles. Citizens and officers are locked out of analyst tools.", 5)

        page.get_by_role("button", name="Crime Analyst").click()
        page.wait_for_timeout(1500)
        shot(page, "02_overview", "Analyst view: one OS across three precincts and five record types.", 5)

        for tab, name, cap in [
            ("sources", "03_sources", "Five federated sources: incidents, forensics, CCTV, witnesses, press (10,000 synthetic records)."),
            ("zetaris", "04_zetaris", "Zetaris data-layer status. This recording uses local data because no Zetaris stack was running."),
            ("incidents", "05_incidents", "Incident browser with station, crime type, status and date filters."),
        ]:
            page.evaluate(f"window.location.hash = '#{tab}'")
            page.wait_for_timeout(1200)
            shot(page, name, cap, 5)

        # Investigation (sample mode)
        page.evaluate("window.location.hash = '#investigation'")
        page.wait_for_timeout(1500)
        shot(page, "06_investigation", "Investigation workbench with preset cross-station scenarios.", 4)
        page.get_by_role("button", name="Commercial Crowbar Safe Cracking Syndicate").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="Run Autonomous Investigation").click()
        page.wait_for_timeout(3000)
        shot(page, "07_result_top", "SAMPLE MODE result: candidate link between INC-NORTH-0042 and INC-CENTRAL-0118.", 6)
        page.mouse.wheel(0, 900)
        shot(page, "08_result_mid", "Each link cites record IDs and a verification status. Scores are uncalibrated.", 6)
        page.mouse.wheel(0, 900)
        shot(page, "09_result_low", "Contradictions and limitations stay visible. No verdict on guilt.", 6)

        page.evaluate("window.location.hash = '#matrix'")
        page.wait_for_timeout(1500)
        shot(page, "10_matrix", "Station correlation matrix and pulse map.", 6)
        page.mouse.wheel(0, 900)
        shot(page, "11_matrix_skeptic", "Skeptic challenge inspector: what was verified and what was struck.", 6)

        page.evaluate("window.location.hash = '#tip_portal'")
        page.wait_for_timeout(1500)
        shot(page, "12_tips", "Anonymous tip portal: in-browser EXIF/GPS stripping and prompt-injection screening.", 6)

        # Role isolation: public citizen cannot reach analyst tools
        page.evaluate("localStorage.clear(); sessionStorage.clear()")
        page.goto(APP)
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="Public Citizen").click()
        page.wait_for_timeout(1200)
        page.evaluate("window.location.hash = '#investigation'")
        shot(page, "13_citizen_blocked", "Role isolation: a citizen who deep-links to the analyst workbench is redirected.", 5)
        browser.close()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/System/Library/Fonts/Helvetica.ttc", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def card(lines: list[tuple[str, int, bool, tuple]]) -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    y = 330
    for text, size, bold, col in lines:
        f = font(size, bold)
        for ln in wrap(d, text, f, W - 240):
            d.text((120, y), ln, font=f, fill=col)
            y += int(size * 1.35)
        y += 20
    return img


def captioned(path: Path, caption: str) -> Image.Image:
    img = Image.open(path).convert("RGB").resize((W, H))
    d = ImageDraw.Draw(img, "RGBA")
    f = font(34, True)
    lines = wrap(d, caption, f, W - 160)
    bar_h = 40 + 46 * len(lines)
    d.rectangle([0, H - bar_h, W, H], fill=(15, 27, 51, 235))
    for i, ln in enumerate(lines):
        d.text((80, H - bar_h + 20 + 46 * i), ln, font=f, fill=WHITE)
    return img


def build_video() -> None:
    frames: list[tuple[Image.Image, float]] = [
        (card([("Cross-Station Crime Intelligence", 84, True, WHITE),
               ("Models propose. Code verifies. A skeptic objects. The officer decides.", 40, False, AMBER),
               ("Open Agent Hackathon 2026  |  Track 1: Solving Fragmented Intelligence", 30, False, (202, 220, 252))]), 5),
    ]
    for name, caption, secs in SCENES or [(p.stem, p.stem, 5.0) for p in sorted(SHOTS.glob("*.png"))]:
        frames.append((captioned(SHOTS / f"{name}.png", caption), secs))
    frames.append((card([("Try it without credentials", 64, True, WHITE),
                         ("docker run -p 8000:8000 -e SAMPLE_MODE=true oah-submission", 34, False, AMBER),
                         ("Investigation scenes in this video ran in SAMPLE MODE (pre-built scenarios, no live agents).", 30, False, (202, 220, 252)),
                         ("Models propose. Code verifies. A skeptic objects. The officer decides.", 30, False, WHITE)]), 6))

    writer = imageio.get_writer(str(OUT), fps=FPS, codec="libx264", quality=7, macro_block_size=1)
    for img, secs in frames:
        arr = np.asarray(img)
        for _ in range(int(secs * FPS)):
            writer.append_data(arr)
    writer.close()
    total = sum(s for _, s in frames)
    print(f"Wrote {OUT} ({total:.0f}s, {len(frames)} scenes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-capture", action="store_true", help="skip screenshots, rebuild video from existing ones")
    args = ap.parse_args()
    procs: list[subprocess.Popen] = []
    try:
        if not args.no_capture:
            procs = start_servers()
            capture()
        build_video()
    finally:
        for pr in procs:
            pr.terminate()


if __name__ == "__main__":
    main()
