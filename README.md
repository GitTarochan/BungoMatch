# 文豪スタイル判定アプリ

AIMathBook（Team Aidemy）の文豪判定機を参考に、  
**「前処理 → 特徴量 → 分類」** の流れをそのまま使って作った Web アプリです。

ユーザーが自由に書いた文章を入力すると、100人の著者コーパスに対して文体の近さを推定し、  
**TOP3の著者**を確率付きで表示します。あわせて各著者の**代表作**と**青空文庫ページリンク**も出力します。

## 主な機能

- 作文しやすいように、テーマ付き入力フォームを用意
- テーマごとに推奨文字数レンジを設定（短すぎ/長すぎをガイド）
- 学習済みモデル（青空文庫コーパス由来）を読み込んでブラウザ上で推論
- 判定結果は TOP3 表示（著者名・確率・代表作・青空文庫リンク）

## 機械学習パイプライン（AIMathBook準拠の構成）

1. 前処理
- 入力文: `NFKC` 正規化 + 空白除去
- 学習コーパス: 青空文庫本文からルビ・注記などを除去して分割

2. 特徴量
- `TfidfVectorizer(analyzer="char", ngram_range=(2,3))`
- 文字 2-gram / 3-gram の TF-IDF

3. 分類
- `LogisticRegression`（多クラス）
- `predict_proba` 相当の確率で順位付け

## 現在の学習済みモデル

- 著者数: **100**
- サンプル数: **9,145**（train 7,316 / test 1,829）
- Accuracy: **0.8387**
- Top-3 Accuracy: **0.9464**
- モデルファイル: `models/author_style_web_model.json`
- 詳細レポート: `models/evaluation_report.md`

（上記は `models/author_style_web_model.json` の `version: 2026-02-24T05:29:13Z` 時点）

## ディレクトリ構成

```text
.
├── index.html
├── styles.css
├── app.js
├── data/
│   ├── corpus/
│   │   ├── aozora_corpus.csv
│   │   ├── aozora_corpus_stats.json
│   │   └── list_person_all_extended_utf8.zip
│   └── raw/
├── scripts/
│   ├── build_aozora_corpus.py
│   └── train_author_model.py
└── models/
    ├── author_style_model.joblib
    ├── author_style_web_model.json
    ├── evaluation_report.json
    └── evaluation_report.md
```

## すぐに動かす（学習済みモデルを使う）

1. 依存パッケージをインストール

```bash
python3 -m pip install -U requests numpy scikit-learn joblib
```

2. ローカルサーバー起動

```bash
python3 -m http.server 8000
```

3. ブラウザで開く

- [http://localhost:8000](http://localhost:8000)

## コーパス再構築と再学習

青空文庫から 100 著者コーパスを再作成し、モデルを再学習する場合:

1. コーパス作成

```bash
python3 scripts/build_aozora_corpus.py \
  --author-count 100 \
  --min-works 30 \
  --works-per-author 160 \
  --target-chunks-per-author 90 \
  --min-chars 100 \
  --max-chars 320
```

2. 学習・評価・Webモデル書き出し

```bash
python3 scripts/train_author_model.py \
  --input-csv data/corpus/aozora_corpus.csv \
  --model-joblib models/author_style_model.joblib \
  --web-model-json models/author_style_web_model.json \
  --report-json models/evaluation_report.json \
  --report-md models/evaluation_report.md \
  --metadata-zip data/corpus/list_person_all_extended_utf8.zip \
  --test-size 0.2 \
  --random-state 42 \
  --max-features 9000
```

## 判定画面の仕様

- 判定候補一覧は事前表示しません
- 出力時に TOP3 を表示
  - 著者名
  - 推定確率
  - 代表作
  - 青空文庫ページリンク

## 参考・クレジット

- 参考実装: [TeamAidemy/AIMathBook](https://github.com/TeamAidemy/AIMathBook)
- コーパス出典: [青空文庫](https://www.aozora.gr.jp/)

