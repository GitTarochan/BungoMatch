#!/usr/bin/env python3
"""Train and evaluate author-style classifier from built corpus."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

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

STYLE_FEATURE_NAMES = [
    "avg_sentence_length",
    "sentence_length_std",
    "sentence_count_log",
    "first_person_rate",
    "emotion_punct_rate",
    "comma_rate",
    "quote_rate",
    "kanji_rate",
    "hiragana_rate",
    "katakana_rate",
]

WORD_TOKEN_PATTERN = re.compile(r"[一-龥々〆ヵヶ]{2,}|[ぁ-ゖー]{2,}|[ァ-ヴー]{2,}|[A-Za-z]{2,}")
PUNCT_PATTERN = re.compile(r"[「」『』（）()［］【】〈〉《》〔〕…・。、，．！？!?ー〜～:：;；\"'`]")
STOPWORD_SET = {word for word in DEFAULT_STOPWORDS if word}


@dataclass(slots=True)
class Sample:
    label: str
    text: str
    work_id: str
    work_title: str
    sample_id: str


def build_stopword_pattern(stopwords: list[str]) -> re.Pattern | None:
    escaped = [re.escape(word) for word in sorted(set(stopwords), key=len, reverse=True) if word]
    if not escaped:
        return None
    return re.compile("|".join(escaped))


STOPWORD_PATTERN = build_stopword_pattern(DEFAULT_STOPWORDS)


def clean_aozora_noise(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"《[^》]*》", "", text)
    text = re.sub(r"［＃[^］]*］", "", text)
    text = text.replace("｜", "")
    text = re.sub(r"^[-=]{20,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^(入力|校正|底本|公開|初出|翻訳|作成)[：:].*$", "", text, flags=re.MULTILINE)
    if "底本：" in text:
        text = text.split("底本：", 1)[0]
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[\t\u3000 ]+", " ", text)
    return text.strip()


def preprocess_text_for_char(text: str) -> str:
    text = clean_aozora_noise(text)
    text = re.sub(r"\s+", "", text)
    text = PUNCT_PATTERN.sub("", text)
    text = re.sub(r"[0-9０-９]+", "", text)
    if STOPWORD_PATTERN is not None:
        text = STOPWORD_PATTERN.sub("", text)
    return text.strip()


def preprocess_text_for_word(text: str) -> str:
    text = clean_aozora_noise(text)
    text = re.sub(r"[0-9０-９]+", " ", text)
    text = PUNCT_PATTERN.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [token for token in WORD_TOKEN_PATTERN.findall(text) if token not in STOPWORD_SET]
    return " ".join(tokens)


def split_space_tokens(text: str) -> list[str]:
    return [token for token in str(text or "").split(" ") if token]


def count_matches(text: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(text))


def extract_style_features(text: str) -> dict[str, float]:
    cleaned = clean_aozora_noise(text)
    compact = re.sub(r"\s+", "", cleaned)
    char_length = max(1, len(compact))

    sentences = [part.strip() for part in re.split(r"[。！？!?]+", cleaned) if part.strip()]
    sentence_count = max(1, len(sentences))
    sentence_lengths = [max(1, len(s)) for s in sentences]

    avg_sentence_length = float(sum(sentence_lengths) / sentence_count)
    sentence_length_std = float(np.std(sentence_lengths))

    first_person_count = count_matches(compact, re.compile(r"私|わたし|僕|ぼく|俺|おれ|わし"))
    emotion_punct_count = count_matches(cleaned, re.compile(r"[！？!?]"))
    comma_count = count_matches(cleaned, re.compile(r"[、，,]"))
    quote_count = count_matches(cleaned, re.compile(r"[「」『』]"))
    kanji_count = count_matches(compact, re.compile(r"[一-龥々〆ヵヶ]"))
    hiragana_count = count_matches(compact, re.compile(r"[ぁ-ゖ]"))
    katakana_count = count_matches(compact, re.compile(r"[ァ-ヴー]"))

    return {
        "avg_sentence_length": avg_sentence_length,
        "sentence_length_std": sentence_length_std,
        "sentence_count_log": float(np.log(sentence_count + 1)),
        "first_person_rate": first_person_count / char_length,
        "emotion_punct_rate": emotion_punct_count / char_length,
        "comma_rate": comma_count / char_length,
        "quote_rate": quote_count / char_length,
        "kanji_rate": kanji_count / char_length,
        "hiragana_rate": hiragana_count / char_length,
        "katakana_rate": katakana_count / char_length,
    }


def style_feature_matrix(texts: list[str]) -> np.ndarray:
    rows = []
    for text in texts:
        feats = extract_style_features(text)
        rows.append([feats[name] for name in STYLE_FEATURE_NAMES])
    return np.asarray(rows, dtype=np.float64)


def to_builtin(value):
    if isinstance(value, dict):
        return {key: to_builtin(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_builtin(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def load_samples(path: Path, min_text_length: int) -> list[Sample]:
    samples: list[Sample] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = (row.get("label") or "").strip()
            work_id = (row.get("work_id") or "").strip()
            text = clean_aozora_noise(row.get("text") or "")
            compact_len = len(re.sub(r"\s+", "", text))
            if not label or not work_id or compact_len < min_text_length:
                continue
            samples.append(
                Sample(
                    label=label,
                    text=text,
                    work_id=work_id,
                    work_title=(row.get("work_title") or "").strip(),
                    sample_id=(row.get("sample_id") or "").strip(),
                )
            )
    if not samples:
        raise RuntimeError(f"No training rows found in {path}")
    return samples


def balance_samples(
    samples: list[Sample],
    *,
    min_works_per_author: int,
    max_works_per_author: int,
    max_chunks_per_work: int,
    max_samples_per_author: int,
    random_state: int,
) -> tuple[list[Sample], dict[str, dict[str, int]]]:
    grouped: dict[str, dict[str, list[Sample]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        grouped[sample.label][sample.work_id].append(sample)

    filtered_authors = sorted([a for a, works in grouped.items() if len(works) >= min_works_per_author])
    if not filtered_authors:
        raise RuntimeError(
            f"No authors satisfy min_works_per_author={min_works_per_author}. "
            "Run corpus build with broader data first."
        )

    rng = random.Random(random_state)
    balanced: list[Sample] = []
    stats: dict[str, dict[str, int]] = {}

    for author in filtered_authors:
        work_ids = sorted(grouped[author])
        rng.shuffle(work_ids)
        selected_work_ids = work_ids[:max_works_per_author]

        author_rows: list[Sample] = []
        used_work_count = 0
        for work_id in selected_work_ids:
            work_rows = list(grouped[author][work_id])
            work_rows.sort(key=lambda item: item.sample_id)
            if len(work_rows) > max_chunks_per_work:
                work_rows = work_rows[:max_chunks_per_work]
            if work_rows:
                used_work_count += 1
                author_rows.extend(work_rows)

        if len(author_rows) > max_samples_per_author:
            author_rows = rng.sample(author_rows, max_samples_per_author)

        balanced.extend(author_rows)
        stats[author] = {
            "available_works": len(grouped[author]),
            "selected_works": len(selected_work_ids),
            "used_works": used_work_count,
            "samples": len(author_rows),
        }

    if not balanced:
        raise RuntimeError("Balancing removed all samples")

    return balanced, stats


def split_by_work(
    samples: list[Sample],
    *,
    test_size: float,
    random_state: int,
) -> tuple[list[Sample], list[Sample], dict[str, dict[str, int]]]:
    grouped: dict[str, dict[str, list[Sample]]] = defaultdict(lambda: defaultdict(list))
    for sample in samples:
        grouped[sample.label][sample.work_id].append(sample)

    rng = random.Random(random_state)
    train: list[Sample] = []
    test: list[Sample] = []
    split_stats: dict[str, dict[str, int]] = {}

    for author in sorted(grouped):
        work_ids = sorted(grouped[author])
        rng.shuffle(work_ids)
        if len(work_ids) < 2:
            raise RuntimeError(f"Author '{author}' has <2 works after balancing; work-based split unavailable")

        test_works = max(1, int(round(len(work_ids) * test_size)))
        test_works = min(test_works, len(work_ids) - 1)
        test_work_ids = set(work_ids[:test_works])

        for work_id in work_ids:
            rows = grouped[author][work_id]
            if work_id in test_work_ids:
                test.extend(rows)
            else:
                train.extend(rows)

        split_stats[author] = {
            "train_works": len(work_ids) - len(test_work_ids),
            "test_works": len(test_work_ids),
            "train_samples": sum(len(grouped[author][wid]) for wid in work_ids if wid not in test_work_ids),
            "test_samples": sum(len(grouped[author][wid]) for wid in test_work_ids),
        }

    if not train or not test:
        raise RuntimeError("Invalid split: train or test is empty")

    return train, test, split_stats


def read_metadata_rows(metadata_zip: Path) -> list[dict[str, str]]:
    if not metadata_zip.exists():
        return []
    with zipfile.ZipFile(metadata_zip) as zf:
        csv_name = zf.namelist()[0]
        raw = zf.read(csv_name).decode("utf-8-sig", errors="ignore")
    return list(csv.DictReader(raw.splitlines()))


def build_representative_map(
    samples: list[Sample], metadata_zip: Path, labels: list[str]
) -> dict[str, dict[str, str]]:
    work_counts: dict[str, Counter] = defaultdict(Counter)
    work_titles: dict[tuple[str, str], str] = {}

    for row in samples:
        work_counts[row.label][row.work_id] += 1
        if row.work_title and (row.label, row.work_id) not in work_titles:
            work_titles[(row.label, row.work_id)] = row.work_title

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

        override = AUTHOR_REPRESENTATIVE_OVERRIDES.get(author, {})
        representative_map[author] = {
            "representative_work": override.get("representative_work", "") or representative_work,
            "aozora_url": override.get("aozora_url", "") or aozora_url,
        }

    return representative_map


def resolve_author_meta(author_name: str, representative_map: dict[str, dict[str, str]]) -> dict[str, str]:
    base = AUTHOR_INFO.get(
        author_name,
        {
            "label": "青空文庫作家",
            "comment": f"{author_name}のコーパスに近い文体傾向です。",
        },
    )
    representative = representative_map.get(author_name, {})
    return {
        "label": base.get("label", ""),
        "comment": base.get("comment", ""),
        "representative_work": representative.get("representative_work", ""),
        "aozora_url": representative.get("aozora_url", ""),
    }


def vectorizer_payload(vectorizer: TfidfVectorizer) -> dict[str, object]:
    vocabulary = {token: int(index) for token, index in vectorizer.vocabulary_.items()}
    index_to_token = [None] * len(vocabulary)
    for token, index in vocabulary.items():
        index_to_token[index] = token

    return {
        "ngram_range": list(vectorizer.ngram_range),
        "norm": vectorizer.norm,
        "idf": vectorizer.idf_.tolist(),
        "vocabulary": vocabulary,
        "index_to_token": index_to_token,
    }


def export_web_model(
    *,
    char_vectorizer: TfidfVectorizer,
    word_vectorizer: TfidfVectorizer,
    style_means: np.ndarray,
    style_scales: np.ndarray,
    classifier: LogisticRegression,
    output_path: Path,
    metrics: dict,
    labels: list[str],
    representative_map: dict[str, dict[str, str]],
    abstain_min_top1: float,
    abstain_min_margin: float,
) -> None:
    char_payload = vectorizer_payload(char_vectorizer)
    word_payload = vectorizer_payload(word_vectorizer)

    char_dim = len(char_payload["index_to_token"])
    word_dim = len(word_payload["index_to_token"])
    style_dim = len(STYLE_FEATURE_NAMES)

    payload = {
        "version": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Aozora Bunko",
        "pipeline": [
            "normalize_and_remove_stopwords",
            "tfidf_char_2_4gram",
            "tfidf_word_1_2gram",
            "style_metrics_standardized",
            "logistic_regression_multinomial",
        ],
        "preprocessing": {
            "normalize": "NFKC",
            "remove_whitespace": True,
            "remove_symbols": True,
            "remove_digits": True,
            "aozora_noise_cleanup": True,
            "stopwords": DEFAULT_STOPWORDS,
        },
        "vectorizers": {
            "char": char_payload,
            "word": word_payload,
        },
        "style_features": {
            "names": STYLE_FEATURE_NAMES,
            "means": style_means.tolist(),
            "scales": style_scales.tolist(),
        },
        "feature_layout": {
            "char": {"offset": 0, "size": char_dim},
            "word": {"offset": char_dim, "size": word_dim},
            "style": {"offset": char_dim + word_dim, "size": style_dim},
            "total_size": char_dim + word_dim + style_dim,
        },
        "decision_policy": {
            "abstain": {
                "enabled": True,
                "min_top1_percent": abstain_min_top1,
                "min_margin_percent": abstain_min_margin,
            }
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

    macro_avg = report["macro avg"]
    weighted_avg = report["weighted avg"]
    lines.append(
        f"| macro avg | {macro_avg['precision']:.3f} | {macro_avg['recall']:.3f} | {macro_avg['f1-score']:.3f} | {int(macro_avg['support'])} |"
    )
    lines.append(
        f"| weighted avg | {weighted_avg['precision']:.3f} | {weighted_avg['recall']:.3f} | {weighted_avg['f1-score']:.3f} | {int(weighted_avg['support'])} |"
    )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train author-style classifier")
    parser.add_argument("--input-csv", default="data/corpus/aozora_corpus_top10.csv")
    parser.add_argument("--model-joblib", default="models/author_style_model.joblib")
    parser.add_argument("--web-model-json", default="models/author_style_web_model.json")
    parser.add_argument("--report-json", default="models/evaluation_report.json")
    parser.add_argument("--report-md", default="models/evaluation_report.md")
    parser.add_argument("--metadata-zip", default="data/corpus/list_person_all_extended_utf8.zip")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--max-features", type=int, default=9000)
    parser.add_argument("--max-char-features", type=int, default=5200)
    parser.add_argument("--max-word-features", type=int, default=3200)
    parser.add_argument("--min-text-length", type=int, default=30)
    parser.add_argument("--min-works-per-author", type=int, default=10)
    parser.add_argument("--max-works-per-author", type=int, default=18)
    parser.add_argument("--max-chunks-per-work", type=int, default=12)
    parser.add_argument("--max-samples-per-author", type=int, default=220)
    parser.add_argument("--abstain-min-top1", type=float, default=36.0)
    parser.add_argument("--abstain-min-margin", type=float, default=7.0)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    raw_samples = load_samples(Path(args.input_csv), min_text_length=args.min_text_length)
    balanced_samples, balance_stats = balance_samples(
        raw_samples,
        min_works_per_author=args.min_works_per_author,
        max_works_per_author=args.max_works_per_author,
        max_chunks_per_work=args.max_chunks_per_work,
        max_samples_per_author=args.max_samples_per_author,
        random_state=args.random_state,
    )

    train_samples, test_samples, split_stats = split_by_work(
        balanced_samples,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    X_train_text = [s.text for s in train_samples]
    y_train = [s.label for s in train_samples]
    X_test_text = [s.text for s in test_samples]
    y_test = [s.label for s in test_samples]

    max_char_features = args.max_char_features
    max_word_features = args.max_word_features
    if args.max_features:
        max_char_features = min(max_char_features, args.max_features)
        max_word_features = min(max_word_features, max(1000, args.max_features - max_char_features))

    char_vectorizer = TfidfVectorizer(
        preprocessor=preprocess_text_for_char,
        analyzer="char",
        ngram_range=(2, 4),
        min_df=2,
        max_features=max_char_features,
        lowercase=False,
        norm="l2",
        smooth_idf=True,
    )
    word_vectorizer = TfidfVectorizer(
        preprocessor=preprocess_text_for_word,
        tokenizer=split_space_tokens,
        token_pattern=None,
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_features=max_word_features,
        lowercase=False,
        norm="l2",
        smooth_idf=True,
    )

    X_train_char = char_vectorizer.fit_transform(X_train_text)
    X_test_char = char_vectorizer.transform(X_test_text)

    X_train_word = word_vectorizer.fit_transform(X_train_text)
    X_test_word = word_vectorizer.transform(X_test_text)

    X_train_style_raw = style_feature_matrix(X_train_text)
    X_test_style_raw = style_feature_matrix(X_test_text)
    style_means = X_train_style_raw.mean(axis=0)
    style_scales = X_train_style_raw.std(axis=0)
    style_scales[style_scales < 1e-9] = 1.0

    X_train_style = (X_train_style_raw - style_means) / style_scales
    X_test_style = (X_test_style_raw - style_means) / style_scales

    X_train_all = sparse.hstack(
        [X_train_char, X_train_word, sparse.csr_matrix(X_train_style)],
        format="csr",
    )
    X_test_all = sparse.hstack(
        [X_test_char, X_test_word, sparse.csr_matrix(X_test_style)],
        format="csr",
    )

    classifier = LogisticRegression(
        max_iter=2400,
        solver="lbfgs",
        C=2.8,
    )
    classifier.fit(X_train_all, y_train)

    y_pred = classifier.predict(X_test_all)
    y_prob = classifier.predict_proba(X_test_all)
    class_labels = classifier.classes_.tolist()

    accuracy = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    top3_idx = np.argsort(y_prob, axis=1)[:, -3:]
    class_to_idx = {label: idx for idx, label in enumerate(class_labels)}
    y_test_idx = np.array([class_to_idx[label] for label in y_test], dtype=int)
    top3_hits = sum(1 for row, truth in zip(top3_idx, y_test_idx, strict=False) if truth in row)
    top3_accuracy = top3_hits / len(y_test_idx)
    report = classification_report(y_test, y_pred, labels=class_labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=class_labels).tolist()

    representative_map = build_representative_map(balanced_samples, Path(args.metadata_zip), class_labels)

    metrics = {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "top3_accuracy": top3_accuracy,
        "classes": class_labels,
        "classification_report": report,
        "confusion_matrix": cm,
        "test_size": args.test_size,
        "random_state": args.random_state,
        "samples": {
            "train": len(train_samples),
            "test": len(test_samples),
            "total": len(balanced_samples),
            "raw_total": len(raw_samples),
        },
        "balance": {
            "min_works_per_author": args.min_works_per_author,
            "max_works_per_author": args.max_works_per_author,
            "max_chunks_per_work": args.max_chunks_per_work,
            "max_samples_per_author": args.max_samples_per_author,
            "authors": balance_stats,
        },
        "work_split": {
            "method": "author-wise work holdout",
            "authors": split_stats,
        },
        "probability_note": "predict_proba from multinomial logistic regression",
        "preprocessing_note": "NFKC normalize + Aozora noise cleanup + remove punctuation/digits/stopwords",
        "feature_note": "TF-IDF(char 2-4gram + word 1-2gram) + standardized style metrics",
        "avg_max_probability": float(np.mean(np.max(y_prob, axis=1))),
    }

    model_path = Path(args.model_joblib)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "char_vectorizer": char_vectorizer,
            "word_vectorizer": word_vectorizer,
            "style_feature_names": STYLE_FEATURE_NAMES,
            "style_means": style_means,
            "style_scales": style_scales,
            "classifier": classifier,
            "stopwords": DEFAULT_STOPWORDS,
            "decision_policy": {
                "abstain": {
                    "enabled": True,
                    "min_top1_percent": args.abstain_min_top1,
                    "min_margin_percent": args.abstain_min_margin,
                }
            },
        },
        model_path,
    )

    report_json = Path(args.report_json)
    report_json.write_text(json.dumps(to_builtin(metrics), ensure_ascii=False, indent=2), encoding="utf-8")

    report_md = Path(args.report_md)
    table = as_markdown_table(report, class_labels)
    report_md.write_text(
        "\n".join(
            [
                "# Evaluation Report",
                "",
                f"- Input: `{args.input_csv}`",
                f"- Balanced samples: **{len(balanced_samples)}** (raw {len(raw_samples)})",
                f"- Train/Test: **{len(train_samples)} / {len(test_samples)}** (work-based split)",
                f"- Accuracy: **{accuracy:.4f}**",
                f"- Macro-F1: **{macro_f1:.4f}**",
                f"- Top-3 Accuracy: **{top3_accuracy:.4f}**",
                f"- Avg max probability: **{metrics['avg_max_probability']:.4f}**",
                "- Preprocess: **NFKC + 青空文庫ノイズ除去 + 記号/数字/ストップワード除外**",
                "- Features: **TF-IDF(char 2-4gram + word 1-2gram) + 文体指標10次元**",
                f"- Balancing: **min works {args.min_works_per_author} / max works {args.max_works_per_author}**",
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

    export_web_model(
        char_vectorizer=char_vectorizer,
        word_vectorizer=word_vectorizer,
        style_means=style_means,
        style_scales=style_scales,
        classifier=classifier,
        output_path=Path(args.web_model_json),
        metrics=metrics,
        labels=class_labels,
        representative_map=representative_map,
        abstain_min_top1=args.abstain_min_top1,
        abstain_min_margin=args.abstain_min_margin,
    )

    print(f"Saved model: {model_path}")
    print(f"Saved web model: {args.web_model_json}")
    print(f"Saved report json: {report_json}")
    print(f"Saved report md: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
