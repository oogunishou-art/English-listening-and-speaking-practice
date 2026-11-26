#!/usr/bin/env bash
# 新しい作業環境で、音声づくり・音声の点検・PDF用の字形づくりの道具をそろえる（1分ほど・約700MB）。
# 使い方: bash dev/setup.sh      （置き場所は GE_TOOLS。決めなければ /tmp/getools）
# アプリの画面のテスト（dev/test）だけなら、この準備はいらない（Playwright と Chromium は最初から入っている）。
set -euo pipefail
T=${GE_TOOLS:-/tmp/getools}; mkdir -p "$T"; cd "$T"
get(){ curl -sSL --retry 3 -o "$2" "$1"; }   # GitHub からのダウンロードはこの作業環境でも通る

echo '1/6 Python の部品'
pip install -q --break-system-packages numpy onnxruntime pyloudnorm soundfile librosa sherpa-onnx praat-parselmouth fonttools 2>&1 | grep -v '^WARNING: Running pip' || true

echo '2/6 Piper（英語の音素づくり。espeak-ng のデータ入り）'
[ -x piper/piper_phonemize ] || { get https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz a.tgz; tar xzf a.tgz; rm a.tgz; }

echo '3/6 英語の声（Ryan＝あなた役の男性、LibriTTS＝女性・ほかの役、イギリス英語の女性）'
mkdir -p voices
for v in en-us-ryan-high en-us-libritts-high en-gb-southern_english_female-low; do
  [ -s voices/$v.onnx ] || { get https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-$v.tar.gz a.tgz; tar xzf a.tgz -C voices; rm a.tgz; }
done

echo '4/6 VOICEVOX（日本語の声：冥鳴ひまり、スタイル14）'
python3 -c 'import voicevox_core' 2>/dev/null || {
  W=voicevox_core-0.17.1-cp310-abi3-manylinux_2_34_x86_64.whl
  get https://github.com/VOICEVOX/voicevox_core/releases/download/0.17.1/$W $W
  pip install -q --break-system-packages ./$W 2>&1 | grep -v '^WARNING: Running pip' || true; rm $W; }
[ -d voicevox_onnxruntime-linux-x64-1.17.3 ] || { get https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz a.tgz; tar xzf a.tgz; rm a.tgz; }
[ -d open_jtalk_dic_utf_8-1.11 ] || { get https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz a.tgz; tar xzf a.tgz; rm a.tgz; }
mkdir -p vvm; [ -s vvm/1.vvm ] || get https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.17.0/1.vvm vvm/1.vvm

echo '5/6 音声認識（英語の音声が原稿どおりに聞こえるかの点検）'
[ -d sherpa-onnx-nemo-ctc-en-conformer-small ] || { get https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-ctc-en-conformer-small.tar.bz2 a.tbz; tar xjf a.tbz; rm a.tbz; }

echo '6/6 ffmpeg（MP3 にする）'
command -v ffmpeg >/dev/null || { apt-get install -y -qq ffmpeg >/dev/null 2>&1 || echo '※ ffmpeg が入れられませんでした'; }

echo "できました：$T"
