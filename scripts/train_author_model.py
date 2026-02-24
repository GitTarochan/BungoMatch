#!/usr/bin/env python3
"""Train and evaluate author-style classifier from built corpus."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

AUTHOR_INFO = {
    "夏目漱石": {
        "label": "理知と皮肉の観察者",
        "comment": "理知的な観察と、感情を少し距離を置いて眺める語りが強く出ています。",
    },
    "太宰治": {
        "label": "自己告白の揺らぎ",
        "comment": "自己告白的な文体が目立ちます。弱さを隠さず差し出す語り口です。",
    },
    "芥川竜之介": {
        "label": "冷静な描写と陰影",
        "comment": "場面描写が先に立ち、人物の内面が遅れて浮かぶ構図が目立ちます。",
    },
    "芥川龍之介": {
        "label": "冷静な描写と陰影",
        "comment": "場面描写が先に立ち、人物の内面が遅れて浮かぶ構図が目立ちます。",
    },
    "宮沢賢治": {
        "label": "自然と宇宙の感応",
        "comment": "自然現象と心情を重ねる、詩的で澄んだ運びが出ています。",
    },
    "樋口一葉": {
        "label": "余情と気配の細工",
        "comment": "語尾の余情と人物の気配をにじませる運びが強めです。",
    },
    "森鴎外": {
        "label": "理性と感情の緊張",
        "comment": "論理性のある運びの中に、抑えた情念がにじむ語りです。",
    },
    "谷崎潤一郎": {
        "label": "美意識と官能の配列",
        "comment": "美の対象を執拗に見つめるような精密な描写が近いです。",
    },
    "江戸川乱歩": {
        "label": "怪奇と論理の二重奏",
        "comment": "異様な空気の演出と、謎を追う運びの両方が現れています。",
    },
    "与謝野晶子": {
        "label": "感情の直截な熱量",
        "comment": "感情を率直に押し出す、勢いのある言葉選びが目立ちます。",
    },
    "泉鏡花": {
        "label": "幻想と雅語の陰影",
        "comment": "現実と幻想の境界をぼかす、装飾的で濃密な語りです。",
    },
}

AUTHOR_REPRESENTATIVE_OVERRIDES = {
    "夏目漱石": {
        "representative_work": "坊っちやん",
        "aozora_url": "https://www.aozora.gr.jp/cards/000148/card50420.html",
    },
    "太宰治": {
        "representative_work": "人間失格",
        "aozora_url": "https://www.aozora.gr.jp/cards/000035/card301.html",
    },
    "芥川竜之介": {
        "representative_work": "羅生門",
        "aozora_url": "https://www.aozora.gr.jp/cards/000879/card127.html",
    },
    "芥川龍之介": {
        "representative_work": "羅生門",
        "aozora_url": "https://www.aozora.gr.jp/cards/000879/card127.html",
    },
    "宮沢賢治": {
        "representative_work": "銀河鉄道の夜",
        "aozora_url": "https://www.aozora.gr.jp/cards/000081/card46322.html",
    },
    "森鴎外": {
        "representative_work": "舞姫",
        "aozora_url": "https://www.aozora.gr.jp/cards/000129/card682.html",
    },
    "樋口一葉": {
        "representative_work": "たけくらべ",
        "aozora_url": "https://www.aozora.gr.jp/cards/000064/card389.html",
    },
    "谷崎潤一郎": {
        "representative_work": "痴人の愛",
        "aozora_url": "https://www.aozora.gr.jp/cards/001383/card58093.html",
    },
    "江戸川乱歩": {
        "representative_work": "怪人二十面相",
        "aozora_url": "https://www.aozora.gr.jp/cards/001779/card57228.html",
    },
    "与謝野晶子": {
        "representative_work": "みだれ髪",
        "aozora_url": "https://www.aozora.gr.jp/cards/000885/card51307.html",
    },
    "泉鏡花": {
        "representative_work": "高野聖",
        "aozora_url": "https://www.aozora.gr.jp/cards/000050/card43466.html",
    },
}

DEFAULT_STOPWORDS = [
    "そして",
    "しかし",
    "また",
    "ただ",
    "または",
    "及び",
    "という",
    "として",
    "について",
    "において",
    "これ",
    "それ",
    "あれ",
    "この",
    "その",
    "あの",
    "ここ",
    "そこ",
    "あそこ",
    "こと",
    "もの",
    "ため",
    "よう",
    "ところ",
    "ので",
    "から",
    "まで",
    "より",
    "です",
    "ます",
    "である",
    "いる",
    "ある",
    "なる",
    "した",
    "して",
    "され",
    "られ",
    "ない",
    "だった",
    "へ",
    "に",
    "を",
    "が",
    "は",
    "も",
    "と",
    "で",
    "や",
    "か",
    "な",
    "の",
    "ね",
    "よ",
    "ぞ",
]


def build_stopword_pattern(stopwords: list[str]) -> re.Pattern | None:
    escaped = [re.escape(word) for word in sorted(set(stopwords), key=len, reverse=True) if word]
    if not escaped:
        return None
    return re.compile("|".join(escaped))


STOPWORD_PATTERN = build_stopword_pattern(DEFAULT_STOPWORDS)


def preprocess_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[「」『』（）()［］【】〈〉《》〔〕…・。、，．！？!?ー〜～:：;；\"'`]", "", text)
    text = re.sub(r"[0-9０-９]+", "", text)
    if STOPWORD_PATTERN is not None:
        text = STOPWORD_PATTERN.sub("", text)
    return text.strip()


def to_builtin(value):
    if isinstance(value, dict):
        return {key: to_builtin(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_builtin(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def resolve_author_meta(author_name: str, representative_map: dict[str, dict[str, str]]) -> dict[str, str]:
    base = AUTHOR_INFO.get(
        author_name,
        {
            "label": "青空文庫作家",
            "comment": f"{author_name}のコーパスに近い文体傾向です。",
        },
    )
    representative = representative_map.get(author_name, {})
    override = AUTHOR_REPRESENTATIVE_OVERRIDES.get(author_name, {})
    return {
        "label": base.get("label", ""),
        "comment": base.get("comment", ""),
        "representative_work": override.get("representative_work", "") or representative.get("representative_work", ""),
        "aozora_url": override.get("aozora_url", "") or representative.get("aozora_url", ""),
    }


def load_dataset(path: Path) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = preprocess_text(row.get("text") or "")
            label = (row.get("label") or "").strip()
            if not text or len(text) < 20 or not label:
                continue
            texts.append(text)
            labels.append(label)

    if not texts:
        raise RuntimeError(f"No training rows found in {path}")

    return texts, labels


def build_pipeline(max_features: int) -> Pipeline:
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 3),
        min_df=2,
        max_features=max_features,
        lowercase=False,
        norm="l2",
        smooth_idf=True,
    )

    classifier = LogisticRegression(
        max_iter=1500,
        solver="lbfgs",
        C=3.0,
    )

    return Pipeline(
        steps=[
            ("tfidf", vectorizer),
            ("clf", classifier),
        ]
    )


def as_markdown_table(report: dict, labels: list[str]) -> str:
    lines = [
        "| class | precision | recall | f1-score | support |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in labels:
        item = report[label]
        lines.append(
            f"| {label} | {item['precision']:.3f} | {item['recall']:.3f} | {item['f1-score']:.3f} | {int(item['support'])} |"
        )

    avg = report["weighted avg"]
    lines.append(
        f"| weighted avg | {avg['precision']:.3f} | {avg['recall']:.3f} | {avg['f1-score']:.3f} | {int(avg['support'])} |"
    )
    return "\n".join(lines)


def read_metadata_rows(metadata_zip: Path) -> list[dict[str, str]]:
    if not metadata_zip.exists():
        return []
    with zipfile.ZipFile(metadata_zip) as zf:
        csv_name = zf.namelist()[0]
        raw = zf.read(csv_name).decode("utf-8-sig", errors="ignore")
    return list(csv.DictReader(raw.splitlines()))


def build_representative_map(
    corpus_csv: Path, metadata_zip: Path, labels: list[str]
) -> dict[str, dict[str, str]]:
    work_counts: dict[str, Counter] = defaultdict(Counter)
    work_titles: dict[tuple[str, str], str] = {}

    with corpus_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            author = (row.get("label") or "").strip()
            work_id = (row.get("work_id") or "").strip()
            work_title = (row.get("work_title") or "").strip()
            if not author or not work_id:
                continue
            work_counts[author][work_id] += 1
            if work_title and (author, work_id) not in work_titles:
                work_titles[(author, work_id)] = work_title

    metadata_lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_metadata_rows(metadata_zip):
        author = ((row.get("姓") or "") + (row.get("名") or "")).strip()
        work_id = (row.get("作品ID") or "").strip()
        if not author or not work_id:
            continue
        metadata_lookup[(author, work_id)] = {
            "title": (row.get("作品名") or "").strip(),
            "url": (row.get("図書カードURL") or "").strip(),
        }

    representative_map: dict[str, dict[str, str]] = {}
    for author in labels:
        top_work_id = ""
        if work_counts.get(author):
            top_work_id = work_counts[author].most_common(1)[0][0]

        representative_work = ""
        aozora_url = ""
        if top_work_id:
            representative_work = work_titles.get((author, top_work_id), "")
            metadata = metadata_lookup.get((author, top_work_id), {})
            representative_work = metadata.get("title", "") or representative_work
            aozora_url = metadata.get("url", "")

        representative_map[author] = {
            "representative_work": representative_work,
            "aozora_url": aozora_url,
        }

    return representative_map


def export_web_model(
    model: Pipeline,
    output_path: Path,
    metrics: dict,
    labels: list[str],
    representative_map: dict[str, dict[str, str]],
) -> None:
    vectorizer: TfidfVectorizer = model.named_steps["tfidf"]
    classifier: LogisticRegression = model.named_steps["clf"]
    vocabulary = {token: int(index) for token, index in vectorizer.vocabulary_.items()}
    index_to_token = [None] * len(vectorizer.vocabulary_)
    for token, index in vocabulary.items():
        index_to_token[index] = token

    payload = {
        "version": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Aozora Bunko",
        "pipeline": ["normalize_and_remove_stopwords", "tfidf_char_2_3gram", "logistic_regression_multinomial"],
        "preprocessing": {
            "normalize": "NFKC",
            "remove_whitespace": True,
            "remove_symbols": True,
            "remove_digits": True,
            "stopwords": DEFAULT_STOPWORDS,
        },
        "vectorizer": {
            "ngram_range": [2, 3],
            "norm": "l2",
            "idf": vectorizer.idf_.tolist(),
            "vocabulary": vocabulary,
            "index_to_token": index_to_token,
        },
        "classifier": {
            "classes": classifier.classes_.tolist(),
            "coef": classifier.coef_.tolist(),
            "intercept": classifier.intercept_.tolist(),
        },
        "authors": {label: resolve_author_meta(label, representative_map) for label in labels},
        "evaluation": metrics,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(to_builtin(payload), ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train author-style classifier")
    parser.add_argument("--input-csv", default="data/corpus/aozora_corpus.csv")
    parser.add_argument("--model-joblib", default="models/author_style_model.joblib")
    parser.add_argument("--web-model-json", default="models/author_style_web_model.json")
    parser.add_argument("--report-json", default="models/evaluation_report.json")
    parser.add_argument("--report-md", default="models/evaluation_report.md")
    parser.add_argument("--metadata-zip", default="data/corpus/list_person_all_extended_utf8.zip")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--max-features", type=int, default=9000)
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    texts, labels = load_dataset(input_csv)

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=labels,
    )

    model = build_pipeline(max_features=args.max_features)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    class_labels = model.named_steps["clf"].classes_.tolist()
    representative_map = build_representative_map(input_csv, Path(args.metadata_zip), class_labels)

    accuracy = accuracy_score(y_test, y_pred)
    top3_idx = np.argsort(y_prob, axis=1)[:, -3:]
    class_to_idx = {label: idx for idx, label in enumerate(class_labels)}
    y_test_idx = np.array([class_to_idx[label] for label in y_test], dtype=int)
    top3_hits = sum(1 for row, truth in zip(top3_idx, y_test_idx, strict=False) if truth in row)
    top3_accuracy = top3_hits / len(y_test_idx)
    report = classification_report(y_test, y_pred, labels=class_labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=class_labels).tolist()

    metrics = {
        "accuracy": accuracy,
        "top3_accuracy": top3_accuracy,
        "classes": class_labels,
        "classification_report": report,
        "confusion_matrix": cm,
        "test_size": args.test_size,
        "random_state": args.random_state,
        "samples": {
            "train": len(X_train),
            "test": len(X_test),
            "total": len(texts),
        },
        "probability_note": "predict_proba from multinomial logistic regression",
        "preprocessing_note": "NFKC normalize + remove punctuation/digits/stopwords",
        "avg_max_probability": float(np.mean(np.max(y_prob, axis=1))),
    }

    model_path = Path(args.model_joblib)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    report_json = Path(args.report_json)
    report_json.write_text(json.dumps(to_builtin(metrics), ensure_ascii=False, indent=2), encoding="utf-8")

    report_md = Path(args.report_md)
    table = as_markdown_table(report, class_labels)
    report_md.write_text(
        "\n".join(
            [
                "# Evaluation Report",
                "",
                f"- Input: `{input_csv}`",
                f"- Total samples: **{len(texts)}**",
                f"- Train/Test: **{len(X_train)} / {len(X_test)}**",
                f"- Accuracy: **{accuracy:.4f}**",
                f"- Top-3 Accuracy: **{top3_accuracy:.4f}**",
                f"- Avg max probability: **{metrics['avg_max_probability']:.4f}**",
                "- Preprocess: **NFKC + 記号/数字/ストップワード除外**",
                "",
                "## Classification Report",
                "",
                table,
                "",
                "## Confusion Matrix (rows=true, cols=pred)",
                "",
                json.dumps(cm, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )

    export_web_model(model, Path(args.web_model_json), metrics, class_labels, representative_map)

    print(f"Saved model: {model_path}")
    print(f"Saved web model: {args.web_model_json}")
    print(f"Saved report json: {report_json}")
    print(f"Saved report md: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
