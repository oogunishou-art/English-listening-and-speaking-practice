# 開発用の道具（アプリの動きには関係しないファイル）

くわしい引き継ぎ書は、Claude のプロジェクト「総合」の資料 `claude/一般英会話アプリ_引き継ぎ書.md` にある。

| ファイル | 中身 |
|---|---|
| `setup.sh` | 音声づくり・点検の道具をそろえる（`bash dev/setup.sh`、1分ほど） |
| `lib/tts.py` | 英語（Piper：Ryan・LibriTTS）と日本語（VOICEVOX 冥鳴ひまり）の音声合成 |
| `lib/check.py` | 音声認識で原稿どおりに聞こえるかの点検、疑問文の文末の上げ下げ |
| `lib/audio.py` | 無音を切る・音量をそろえる・MP3 にする・確かめる |
| `lib/packlib.py` | 追加の音声ファイル `geadd-*.bin` づくり、index.html の DATA・AUDIO の読み書き |
| `lib/ipa_ja.py` | 表示用の発音記号（英和辞典ふう）づくり |
| `tools/pdf_fonts.py` | PDF 用の字形ファイル `pdf-fonts-*.bin` の点検と作り直し |
| `test/smoke.py` | 全タブを3つの画面サイズで開き、エラーと横のはみ出しを確かめる |
| `test/srv.py` | テスト用サーバー（Range 対応） |
| `examples/integrate_code.py` | 見本：画面・動きだけを変えるときの組み込み方 |
| `examples/integrate_audio.py` | 見本：フレーズを音声つきで足すときの組み込み方 |

```bash
git clone https://github.com/oogunishou-art/English-listening-and-speaking-practice.git
cd English-listening-and-speaking-practice
python3 dev/test/smoke.py                      # いまのアプリを確かめる
python3 dev/test/smoke.py --index out/index.html  # 新しい index.html を確かめる
bash dev/setup.sh                              # 音声を作るときだけ
```
