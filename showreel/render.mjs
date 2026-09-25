// Renders index.html frame-by-frame with headless Chromium and encodes with ffmpeg.
//   node render.mjs                 -> showreel.mp4 (1080p60, with audio.wav if present)
//   node render.mjs --stills 1,2.6  -> stills/t-<sec>.png for quick review
import { chromium } from 'playwright';
import { spawn, execSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const FPS = 60, DURATION = 15;
const ffmpeg = process.env.FFMPEG ||
  execSync('python3 -c "import imageio_ffmpeg as i;print(i.get_ffmpeg_exe())"').toString().trim();

const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error(e); process.exit(1); });
await page.goto(pathToFileURL(join(here, 'index.html')).href + '?render');
await page.evaluate(() => window.READY);
const canvas = page.locator('#c');
const frameAt = t => page.evaluate(([t, fps]) => window.render(t, fps), [t, FPS]).then(() => canvas.screenshot({ type: 'png' }));

const stillsArg = process.argv.indexOf('--stills');
if (stillsArg > -1) {
  mkdirSync(join(here, 'stills'), { recursive: true });
  for (const t of process.argv[stillsArg + 1].split(',').map(Number)) {
    const png = await frameAt(t);
    const { writeFileSync } = await import('node:fs');
    writeFileSync(join(here, 'stills', `t-${t.toFixed(2)}.png`), png);
  }
  await browser.close();
  process.exit(0);
}

const audio = join(here, 'audio.wav');
const args = ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-'];
if (existsSync(audio)) args.push('-i', audio, '-c:a', 'aac', '-b:a', '256k', '-shortest');
args.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', join(here, 'showreel.mp4'));
const enc = spawn(ffmpeg, args, { stdio: ['pipe', 'ignore', 'inherit'] });

const total = FPS * DURATION, t0 = Date.now();
for (let f = 0; f < total; f++) {
  const png = await frameAt(f / FPS);
  if (!enc.stdin.write(png)) await new Promise(r => enc.stdin.once('drain', r));
  if (f % 60 === 0) process.stdout.write(`frame ${f}/${total}  ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
}
enc.stdin.end();
await new Promise(r => enc.on('close', r));
await browser.close();
console.log('done ->', join(here, 'showreel.mp4'));
