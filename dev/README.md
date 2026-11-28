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
| `test/crawl.py` | 総点検：全タブのボタンを2段まで自動で押し、エラー・はみ出し・ほかのタブが開けなくなる不具合を出す（20〜30分） |
| `test/ear.py` | 総点検：音声を流して、イヤホンの次へ・前へ・猶予・連打・一時停止と、声のお知らせ7種を確かめる |
| `test/nav.py` | 総点検：戻るボタン（タブ・設定・検索・ドライブモード・座学モード） |
| `test/pdf_all.py` | 総点検：PDF を種類×用紙×テストで作り、「?」になった文字と確認テストの抜けを出す（/tmp/ge-pdf） |
| `test/make_store.py` | 2か月ほど使った人の記録（store_rich.json）を作る。crawl.py --store などに渡す |
| `test/pwh.py` | 上のテストの共通部品（テスト用サイト・サーバー・ページを開く） |
| `examples/integrate_code.py` | 見本：画面・動きだけを変えるときの組み込み方 |
| `examples/integrate_audio.py` | 見本：フレーズを音声つきで足すときの組み込み方 |

```bash
git clone https://github.com/oogunishou-art/English-listening-and-speaking-practice.git
cd English-listening-and-speaking-practice
python3 dev/test/smoke.py                      # いまのアプリを確かめる
python3 dev/test/smoke.py --index out/index.html  # 新しい index.html を確かめる
bash dev/setup.sh                              # 音声を作るときだけ
```
