# 文豪スタイル判定アプリ

AIMathBook（Team Aidemy）の文豪判定機を参考に、  
**「前処理 → 特徴量 → 分類」** の流れをそのまま使って作った Web アプリです。

ユーザーが自由に書いた文章を入力すると、有名文豪10人コーパスに対して文体の近さを推定し、  
**TOP3の著者**を確率付きで表示します。あわせて各著者の**代表作**と**青空文庫ページリンク**も出力します。

## 主な機能

- 作文しやすいように、テーマ付き入力フォームを用意
- テーマごとに推奨文字数レンジを設定（短すぎ/長すぎをガイド）
- 入力画面に、判定候補10人の「名前＋代表作」を事前表示
- 学習済みモデル（青空文庫コーパス由来）を読み込んでブラウザ上で推論
- 前処理でストップワード除外を実施し、内容語の寄与を強化
- 判定結果は TOP3 表示（著者名・確率・代表作・青空文庫リンク）

## 機械学習パイプライン（AIMathBook準拠の構成）

1. 前処理
- 入力文: `NFKC` 正規化 + 空白/記号/数字/ストップワード除去
- 学習コーパス: 青空文庫本文からルビ・注記などを除去して分割

2. 特徴量
- `TfidfVectorizer(analyzer="char", ngram_range=(2,3))`
- 文字 2-gram / 3-gram の TF-IDF

3. 分類
- `LogisticRegression`（多クラス）
- `predict_proba` 相当の確率で順位付け

## 現在の学習済みモデル（トップ10）

- 著者数: **10**
- サンプル数: **958**（train 766 / test 192）
- Accuracy: **0.9583**
- Top-3 Accuracy: **0.9948**
- モデルファイル: `models/author_style_web_model.json`
- 詳細レポート: `models/evaluation_report.md`

（上記は `models/author_style_web_model.json` の `version: 2026-02-24T08:24:18Z` 時点）

## ディレクトリ構成

```text
.
├── index.html
├── styles.css
├── app.js
├── data/
│   ├── corpus/
│   │   ├── aozora_corpus.csv
│   │   ├── aozora_corpus_top10.csv
│   │   ├── aozora_corpus_top10_stats.json
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

## トップ10データ再作成と再学習

既存の青空文庫コーパスからトップ10著者に絞って再学習する場合:

1. 対象著者ファイルを作成（`data/corpus/top10_famous_authors.txt`）

```bash
cat > data/corpus/top10_famous_authors.txt <<'EOF2'
夏目漱石
太宰治
芥川竜之介
宮沢賢治
森鴎外
樋口一葉
谷崎潤一郎
江戸川乱歩
与謝野晶子
泉鏡花
EOF2
```

2. 10人分CSVを抽出

```bash
python3 - <<'PY'
import csv
from pathlib import Path

authors = set(Path("data/corpus/top10_famous_authors.txt").read_text(encoding="utf-8").splitlines())
src = Path("data/corpus/aozora_corpus.csv")
dst = Path("data/corpus/aozora_corpus_top10.csv")

with src.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = [row for row in reader if row["label"] in authors]
    fieldnames = reader.fieldnames

with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
```

3. 学習・評価・Webモデル書き出し

```bash
python3 scripts/train_author_model.py \
  --input-csv data/corpus/aozora_corpus_top10.csv \
  --model-joblib models/author_style_model.joblib \
  --web-model-json models/author_style_web_model.json \
  --report-json models/evaluation_report.json \
  --report-md models/evaluation_report.md \
  --metadata-zip data/corpus/list_person_all_extended_utf8.zip \
  --test-size 0.2 \
  --random-state 42 \
  --max-features 5000
```

## 判定画面の仕様

- 判定候補10人（名前＋代表作）を入力画面で事前表示
- 判定ボタン押下後、判定中アニメーションを表示
- 出力時に TOP3 を表示
  - 著者名
  - 推定確率
  - 代表作
  - 青空文庫ページリンク

## 参考・クレジット

- 参考実装: [TeamAidemy/AIMathBook](https://github.com/TeamAidemy/AIMathBook)
- コーパス出典: [青空文庫](https://www.aozora.gr.jp/)
