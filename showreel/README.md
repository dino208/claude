# Performance Transformation Showreel

A 15-second, 1080p60 motion-graphics résumé reel (`showreel.mp4`) with a soundtrack synthesised to match.

Everything is code:

- `index.html`: the animation. Its `render(t)` function is deterministic. Open the page in a browser for a live preview, and click to play the audio. Edit `CFG` at the top to change the name, role, metrics and keywords.
- `audio.py`: synthesises `audio.wav` (120 BPM) with numpy and scipy. The hits land on the visual cues.
- `render.mjs`: renders the frames with headless Chromium (Playwright) and pipes them to ffmpeg (H.264 + AAC).

```sh
pip install numpy scipy imageio-ffmpeg
python3 audio.py
node render.mjs                  # -> showreel.mp4
node render.mjs --stills 3.6,7.2 # quick review frames
```
