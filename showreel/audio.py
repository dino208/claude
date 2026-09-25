"""Synthesises the 15 s soundtrack (120 BPM), locked to the visual timeline in index.html."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR, DUR = 48000, 15.0
N = int(SR * DUR)
rng = np.random.default_rng(4)
mix = np.zeros((N, 2))
bus_verb = np.zeros((N, 2))  # send bus → reverb


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def env(n, a=.002, d=.3, curve=1.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d) ** curve
    return e


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f, SR / 2.1), 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)


def place(sig, t, gain=1.0, pan=0.0, verb=0.0):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[:N - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:i + len(sig), 0] += sig * gain * l * 1.414
    mix[i:i + len(sig), 1] += sig * gain * r * 1.414
    if verb:
        bus_verb[i:i + len(sig), 0] += sig * gain * verb
        bus_verb[i:i + len(sig), 1] += sig * gain * verb


def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for d in (-detune, 0, detune) if detune else (0,):
        ph = rng.random()
        out += 2 * ((t * f * (1 + d) + ph) % 1) - 1
    return out / (3 if detune else 1)


# ── drum voices ─────────────────────────────────────────────
def kick(big=False):
    n = int(SR * (1.2 if big else .45))
    t = np.arange(n) / SR
    f = 42 + (160 if big else 120) * np.exp(-t * (18 if big else 30))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .5 if big else .18)
    click = hp(rng.standard_normal(n), 3000) * env(n, .0005, .004)
    return np.tanh((body + click * .4) * 1.8)


def clap():
    n = int(SR * .35)
    x = bp(rng.standard_normal(n), 900, 5000)
    e = np.zeros(n)
    for o in (0, .011, .022):
        i = int(o * SR); e[i:] += env(n - i, .0005, .012 if o < .02 else .12)
    return x * e * .9


def hat(open_=False):
    n = int(SR * (.25 if open_ else .06))
    return hp(rng.standard_normal(n), 7500) * env(n, .0005, .08 if open_ else .015)


def impact(size=1.0):
    n = int(SR * 3)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-t * 6)) / SR) * env(n, .001, .9 * size)
    crash = hp(rng.standard_normal(n), 1800) * env(n, .001, .7 * size) * .35
    return np.tanh(boom * 1.6) + crash


def whoosh(dur, up=True):
    n = int(SR * dur)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 1024
    for s in range(0, n, seg):
        p = s / n
        fc = 300 + 6000 * (p if up else 1 - p) ** 2
        out[s:s + seg] = bp(x[s:s + seg + 512], fc * .7, fc * 1.3)[:len(out[s:s + seg])]
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** (1.5 if up else 3)
    return out * shape


def riser(dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    p = t / dur
    tone = np.sin(2 * np.pi * np.cumsum(midi(57) * 2 ** (p * 2)) / SR) * .3
    return (whoosh(dur) * .8 + tone) * p ** 2


def stab(notes, dur=.5, cutoff=3000, detune=.008):
    n = int(SR * dur)
    x = sum(saw(midi(m), n, detune) for m in notes) / len(notes)
    e = env(n, .002, dur / 3)
    return lp(x, cutoff) * e


def pluck(m, dur=.35, bright=5000):
    n = int(SR * dur)
    x = saw(midi(m), n) * .6 + np.sin(2 * np.pi * midi(m + 12) * np.arange(n) / SR) * .4
    return lp(x, bright) * env(n, .001, .09)


def bell(m, dur=1.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = midi(m)
    return (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
            + .25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12)) * env(n, .001, .5)


def pad(notes, t0, t1, cut=1400, gain=.12, fade=(.4, .6)):
    n = int(SR * (t1 - t0))
    x = sum(saw(midi(m), n, .012) for m in notes) / len(notes)
    x = lp(x, cut)
    e = np.ones(n)
    a, r = int(fade[0] * SR), int(fade[1] * SR)
    e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r)
    place(x * e, t0, gain, verb=.4)


def bass(m, t, dur=.24, gain=.5, cut=600):
    n = int(SR * dur)
    x = saw(midi(m), n) * .6 + np.sin(2 * np.pi * midi(m) * np.arange(n) / SR)
    place(np.tanh(lp(x, cut) * env(n, .003, dur * .6) * 1.5), t, gain)


# ── arrangement ─────────────────────────────────────────────
BEAT = .5
# 0–2: heartbeat. Times solved from the EKG head in sceneIntro.
def ekg_time(x, W=1920):
    ts = np.linspace(.05, 1.8, 20000)
    p = (ts - .05) / 1.75
    e = np.where(p < .5, 4 * p ** 3, 1 - (-2 * p + 2) ** 3 / 2)
    return ts[np.argmin(np.abs(e * (W + 100) - 50 - x))]

for bx in (520, 1160, 1640):
    tb = ekg_time(bx)
    place(lp(kick(), 400), tb - .015, .55)
    place(lp(kick(), 300), tb + .14, .3)
    place(bell(93, .6) * .3, tb, .18, pan=.3, verb=.6)
pad([57, 60, 64, 71], 0, 2.1, cut=900, gain=.10, fade=(.8, .2))
place(riser(.9), 1.1, .45)

# 2–4: role slam
place(impact(1.0), 2.0, .8, verb=.3)
for i, t in enumerate((2.0, 2.5, 3.0)):
    place(stab([57, 64, 69, 72] if i < 2 else [53, 60, 65, 69], .6, 3500), t, .38, verb=.5)
place(whoosh(.35, up=False), 3.7, .5, pan=-.4)
pad([45, 57, 64], 2.0, 4.0, cut=700, gain=.08)

# 4–6: BEFORE — dissonant, glitchy
for k in range(8):
    t = 4.0 + k * .25
    bass(41 if k < 4 else 40, t, .22, .45, 400)
for _ in range(26):
    t = 4.0 + rng.random() * 1.95
    n = int(SR * (.01 + rng.random() * .04))
    blip = np.sign(np.sin(2 * np.pi * (200 + rng.random() * 2500) * np.arange(n) / SR))
    place(blip * env(n, .0005, .02), t, .09, pan=rng.random() * 1.6 - .8)
pad([53, 56, 59, 64], 4.0, 6.0, cut=1100, gain=.1, fade=(.1, .05))
for k in range(8):  # snare roll into the turnaround
    place(clap(), 5.5 + k * .0625, .15 + k * .05)
place(riser(.95), 5.0, .6)
place(whoosh(.25), 5.76, .5, pan=.5)

# 6: TRANSFORM
place(impact(1.4), 6.0, 1.0, verb=.5)
place(stab([48, 55, 60, 64, 67, 72], 1.2, 5000, .012), 6.0, .45, verb=.7)

# 6.5–9: AFTER — major lift + arps
prog_after = [(6.5, 48, [60, 64, 67, 71]), (7.5, 43, [59, 62, 67, 71]), (8.5, 45, [60, 64, 69, 72])]
for t0, root, chord in prog_after:
    for k in range(int(2 / .25) if t0 < 8.5 else 2):
        bass(root, t0 + k * .25, .2, .5, 900)
    for k in range(8 if t0 < 8.5 else 2):
        m = chord[k % 4] + (12 if k >= 4 else 0)
        place(pluck(m), t0 + k * .125, .22, pan=.5 if k % 2 else -.5, verb=.35)
pad([60, 64, 67, 71], 6.4, 9.0, cut=2500, gain=.08)
for i in range(4):  # counter ticks under each KPI card
    for k in range(10):
        place(pluck(96 + (k % 3), .04, 9000), 6.8 + i * .25 + k * .07, .06, pan=.6 if i % 2 else -.6)

# 9–11: playbook steps
place(impact(.6), 9.0, .45, verb=.4)
for i, (t, m) in enumerate(zip((9.0, 9.45, 9.9, 10.35), (76, 79, 83, 88))):
    place(bell(m, 1.4), t, .22, pan=(-.4, .4, -.2, .2)[i], verb=.8)
    place(stab([m - 24, m - 17, m - 12], .35, 2500), t, .2)
for t0, root in ((9.0, 41), (10.0, 43)):
    for k in range(8):
        bass(root, t0 + k * .125, .1, .45, 1000)
pad([53, 57, 60, 64], 9.0, 11.0, cut=1800, gain=.07)

# 11–12: keyword strobe — a stab on every word
for k in range(8):
    place(stab([57 + (k % 4) * 2, 64 + (k % 4) * 2], .12, 6000), 11 + k * .125, .55, pan=(-.5, .5)[k % 2])
    place(kick(), 11 + k * .125, .75)
place(riser(1.0), 11.0, .8)

# 12–15: signature
place(impact(1.6), 12.0, 1.1, verb=.6)
place(stab([36, 48, 55, 60, 64, 67, 74], 2.5, 3000, .015), 12.0, .5, verb=.8)
pad([48, 55, 60, 64, 67, 74], 12.0, 15.0, cut=2200, gain=.13, fade=(.05, 1.4))
for k, m in enumerate([72, 76, 79, 84, 86, 91, 88, 84]):
    place(pluck(m, .5, 7000), 12.9 + k * .125, .12, pan=(-.6, .6)[k % 2], verb=.9)
place(bell(84, 2.2), 13.4, .15, verb=1.0)

# groove: kicks, claps, hats from 2 → 11
for b in range(int(2 / BEAT), int(11 / BEAT)):
    t = b * BEAT
    if 5.5 <= t < 6.5:  # breath around the turnaround
        continue
    place(kick(), t, .7)
    if b % 2 == 1:
        place(clap(), t, .38, verb=.25)
    place(hat(), t + .25, .2, pan=.3)
    if t >= 6.5:
        place(hat(), t + .125, .08, pan=-.3)
        place(hat(), t + .375, .08, pan=-.3)

# ── master: reverb, sidechain-ish ducking, limiter ─────────
ir_n = int(SR * 2.2)
ir = rng.standard_normal((ir_n, 2)) * np.exp(-np.arange(ir_n) / SR * 3.2)[:, None]
ir = np.stack([lp(ir[:, 0], 6000), lp(ir[:, 1], 6000)], 1)
verb = np.stack([fftconvolve(bus_verb[:, c], ir[:, c])[:N] for c in range(2)], 1)
mix += verb * .12

# bus compressor: 4:1 above threshold on a 30 ms envelope
level = lp(np.abs(mix).max(1), 30)
level = np.maximum(level, 1e-6) / level.max()
thr = .12
gain = np.where(level > thr, (level / thr) ** (1 / 4 - 1), 1.0)
mix *= gain[:, None]
mix /= np.percentile(np.abs(mix), 99.9)
out = np.tanh(mix * 1.1)
out /= np.max(np.abs(out)) / .93
fade = int(.35 * SR)
out[-fade:] *= np.linspace(1, 0, fade)[:, None]
wavfile.write('audio.wav', SR, (out * 32767).astype(np.int16))
print('audio.wav', out.shape, 'peak', np.max(np.abs(out)))
