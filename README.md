# BungoMatch — 文豪スタイル判定アプリ

入力した日本語文章を、青空文庫由来の文豪10人のコーパスで学習したモデルで分類し、
上位3人の候補と代表作を表示するWebアプリです。
文章を書き、その判定をきっかけに文学作品を知る体験を目指しています。

**Pythonでのデータ処理・学習・評価から、JavaScriptによるブラウザ内推論までを含むリポジトリです。**

## できること

- テーマと推奨文字数を参考に文章を入力
- 判定候補となる文豪10人と代表作を事前に確認
- 上位3人の分類結果、推定確率、代表作、青空文庫へのリンクを表示
- 文体指標や判定に寄与する語句を使った分析表示
- 判定の確信度が低い場合の案内

対象著者：与謝野晶子、夏目漱石、太宰治、宮沢賢治、森鴎外、
樋口一葉、江戸川乱歩、泉鏡花、芥川竜之介、谷崎潤一郎。

## 技術構成

| 処理 | 実装 |
|---|---|
| コーパス作成 | Python、requests、青空文庫の本文・作品メタデータ |
| 前処理 | NFKC正規化、ルビ・注記の除去、特徴量ごとの文字・トークン処理 |
| 文字特徴量 | 文字2–4gramのTF-IDF |
| トークン特徴量 | 正規表現で抽出したトークンの1–2gram TF-IDF（形態素解析器は不使用） |
| 文体特徴量 | 文長、句読点、一人称、文字種比率など10次元を標準化 |
| 分類 | scikit-learnの多クラスロジスティック回帰 |
| Web推論 | 語彙・IDF・係数などをJSONに書き出し、JavaScriptで特徴量計算と分類 |
| 画面 | HTML、CSS、JavaScript |

モデルJSONを読み込んだ後の文章の特徴量計算・分類はブラウザ内で行います。
入力文章を外部の推論APIへ送る構成ではありません。

## 評価結果

同梱Webモデルのバージョン：**2026-02-25T02:25:03Z**

著者ごとに**作品単位で学習・テストを分離**しています。
同じ作品から切り出した断片が両方に入ることで、評価が過大になるのを避ける設計です。

| 項目 | 値 |
|---|---:|
| 著者数 | 10 |
| 全サンプル数（文章断片） | 1,271 |
| 学習サンプル数 | 1,014 |
| テストサンプル数 | 257 |
| Accuracy | 68.87% |
| Macro-F1 | 0.6894 |
| Top-3 Accuracy | 84.44% |

[著者別の評価・混同行列](models/evaluation_report.md) /
[評価JSON](models/evaluation_report.json)

これらは同梱モデルの保存済み評価値です。
旧READMEのAccuracy 95.83%・Top-3 Accuracy 99.48%は旧モデルの値であり、
現在のモデルの評価としては使用していません。異なるデータ・評価条件の値は単純比較できません。

## ローカルで試す

必要なもの：Git、Python 3、JavaScriptが動作するブラウザ。

```bash
git clone https://github.com/GitTarochan/BungoMatch.git
cd BungoMatch
python3 -m http.server 8000
```

[http://localhost:8000](http://localhost:8000) を開き、
テーマを選んで文章を入力し、判定ボタンを押してください。
学習済みモデルを試すだけなら、学習用パッケージのインストールは不要です。

モデルJSONを取得するため、HTMLの直接起動ではなくHTTPサーバー経由で開いてください。

## 再学習

以下は同梱の10著者CSVから学習する手順です。
学習コードの型表記に対応した **Python 3.10以上** を使用してください。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install requests numpy scipy scikit-learn joblib
python scripts/train_author_model.py \
  --input-csv data/corpus/aozora_corpus_top10.csv \
  --model-joblib models/author_style_model.joblib \
  --web-model-json models/author_style_web_model.json \
  --report-json models/evaluation_report.json \
  --report-md models/evaluation_report.md \
  --metadata-zip data/corpus/list_person_all_extended_utf8.zip \
  --test-size 0.2 \
  --random-state 42 \
  --max-char-features 5200 \
  --max-word-features 3200 \
  --min-works-per-author 10 \
  --max-works-per-author 18 \
  --max-chunks-per-work 12 \
  --max-samples-per-author 220
```

Windowsでは仮想環境の有効化を `.venv\Scripts\activate` に置き換えてください。
この操作はローカルのモデル・評価ファイルを更新します。
依存ライブラリのバージョンは固定していないため、保存済み評価値との完全一致は保証しません。

コーパス作成スクリプトのオプションは次のコマンドで確認できます。

```bash
python scripts/build_aozora_corpus.py --help
python scripts/train_author_model.py --help
```

## コードを読む場合

| ファイル | 内容 |
|---|---|
| [scripts/build_aozora_corpus.py](scripts/build_aozora_corpus.py) | 本文取得、ノイズ除去、コーパス作成 |
| [scripts/train_author_model.py](scripts/train_author_model.py) | 作品単位の分割、特徴量、学習、評価、JSON出力 |
| [app.js](app.js) | ブラウザ内推論と結果表示 |
| [index.html](index.html) / [styles.css](styles.css) | 入力・結果画面 |
| [models/evaluation_report.md](models/evaluation_report.md) | 保存済みの評価結果 |

## 制約・今後の検証

- 評価は青空文庫内の著者分類に対するものです。一般ユーザーの文章に対する精度は未検証です。
- 語彙や話題、時代による表記の違いも判定に影響します。
- 表示確率は分類モデルの出力で、文体の類似度や文学的評価を直接測ったものではありません。
- 候補は10人に限定されます。候補外の著者や文章でも、この集合に対する判定になります。
- 著者ごとのサンプル数・性能に差があります。クラス別評価も併せて確認してください。
- 今後の検証課題は、特徴量ごとの比較、複数の作品分割での評価、PythonとJavaScriptの推論結果の一致確認です。

## 参考・データ出典

- 参考実装：[TeamAidemy/AIMathBook](https://github.com/TeamAidemy/AIMathBook)
- コーパス出典：[青空文庫](https://www.aozora.gr.jp/)

参考実装の「前処理→特徴量→分類」という構成を出発点にした学習作品です。
現在の実装には、作品単位の評価、複数特徴量の結合、Web用モデル出力、
ブラウザ内推論、代表作への導線が含まれます。

コードの参照元とコーパスの出典は別に扱い、データを再利用する場合は
各作品の著者・翻訳者・底本等の情報と青空文庫の利用条件を確認してください。
