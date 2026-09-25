# Performance Transformation Showreel

A 15-second, 1080p60 motion-graphics résumé reel (`showreel.mp4`) with a soundtrack synthesised to match.

Everything is code:

- `index.html`: the animation, fully self-contained (fonts and score embedded as data URIs). Its `render(t)` function is deterministic. Open the page in any browser for a live preview, and click to play the sound. Edit `CFG` at the top to change the name, role, metrics and keywords.
- `audio.py`: synthesises `audio.wav` (120 BPM) with numpy and scipy. The hits land on the visual cues.
- `render.mjs`: renders the frames with headless Chromium (Playwright) and pipes them to ffmpeg (H.264 + AAC).

```sh
pip install numpy scipy imageio-ffmpeg
python3 audio.py
node render.mjs                  # -> showreel.mp4 (muxes audio.wav)
node render.mjs --stills 3.6,7.2 # quick review frames
```

The preview's embedded score is an AAC copy of `audio.wav`. If you regenerate the audio, re-encode it and replace the base64 in the `#score` tag.
