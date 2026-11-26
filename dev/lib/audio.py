"""音声の整え方（無音を切る・音量をそろえる・MP3 にする・確かめる）。
アプリの音声はすべて 24kHz・モノラル・MP3 48kbps、音量は -18 LUFS にそろえている。"""
import subprocess, wave, numpy as np, pyloudnorm as pyln
SR = 24000

def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return sr, x

def save_wav(path, a, sr):
    a = np.asarray(a, np.float64); a = np.clip(a / max(1e-6, np.max(np.abs(a))) * 0.9, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 32767).astype(np.int16).tobytes())

def trim(x, sr, pad=0.05):
    fr = int(0.01 * sr); n = len(x) // fr
    rms = np.sqrt(np.mean(x[:n * fr].reshape(n, fr) ** 2, axis=1)); th = max(rms.max() * 0.02, 1e-4)
    idx = np.where(rms > th)[0]
    a = max(0, idx[0] * fr - int(pad * sr)); b = min(len(x), (idx[-1] + 1) * fr + int(pad * sr)); return x[a:b]

def fade(x, sr, ms=6):
    n = min(int(sr * ms / 1000), len(x) // 2); r = np.linspace(0, 1, n); x = x.copy(); x[:n] *= r; x[-n:] *= r[::-1]; return x

def normalize(x, sr, target=-18.0):
    L = pyln.Meter(sr, block_size=0.2).integrated_loudness(x) if len(x) > sr * 0.2 else -99
    if not np.isfinite(L) or L < -70: L = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) - 3
    y = x * (10 ** ((target - L) / 20)); pk = np.max(np.abs(y))
    if pk > 0.89:
        t = 0.8; s = np.sign(y); a = np.abs(y); a = np.where(a > t, t + (1 - t) * np.tanh((a - t) / (1 - t)), a); y = s * a * 0.98
    return y

def encode(y, sr, out):
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(sr), '-ac', '1', '-i', '-', '-af', f'aresample={SR}:resampler=soxr',
                    '-ar', str(SR), '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '48k', '-id3v2_version', '0', out], input=pcm, check=True)

def verify(path, expect_s):
    """MP3 を読み直して、長さと音の有無を確かめる。よければ長さ（ミリ秒）を返す"""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    if r.returncode or r.stderr.strip(): return None
    got = len(r.stdout) / 2 / SR
    if abs(got - expect_s) > 0.12: return None
    x = np.frombuffer(r.stdout, np.int16)
    return round(got * 1000, 1) if np.max(np.abs(x)) > 300 else None

def gaps(a, sr, db=-38, min_ms=300):
    """文の途中の無音（min_ms 以上）の一覧 [(始め秒, 終わり秒)]。不自然な間の点検に使う"""
    fr = int(sr * 0.01); n = len(a) // fr
    if n < 3: return []
    r = 20 * np.log10(np.sqrt((np.asarray(a[:n * fr], np.float64).reshape(n, fr) ** 2).mean(1)) + 1e-9)
    r -= r.max(); sil = r < db; out = []; i = 0
    vo = np.where(~sil)[0]
    if not len(vo): return []
    i = vo[0]
    while i <= vo[-1]:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if (j - i) * 10 >= min_ms and j <= vo[-1]: out.append((i / 100, j / 100))
            i = j
        else: i += 1
    return out
