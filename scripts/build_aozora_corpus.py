#!/usr/bin/env python3
"""Build author corpus from Aozora Bunko metadata and text files."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import requests

METADATA_URL = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"
USER_AGENT = "BungoStyleModelBuilder/2.0"


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


@dataclass
class Work:
    work_id: str
    title: str
    release_date: str
    text_url: str


def fetch_bytes(url: str, timeout: int = 45, retries: int = 3) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            wait = attempt * 1.5
            eprint(f"[retry {attempt}/{retries}] fetch failed: {url} ({exc})")
            time.sleep(wait)

    assert last_error is not None
    raise last_error


def ensure_metadata_zip(path: Path, force: bool = False) -> Path:
    if path.exists() and not force:
        return path

    eprint(f"Downloading metadata: {METADATA_URL}")
    content = fetch_bytes(METADATA_URL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def read_metadata_rows(zip_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = zf.namelist()[0]
        raw = zf.read(csv_name).decode("utf-8-sig", errors="ignore")
    return list(csv.DictReader(raw.splitlines()))


def author_full_name(row: dict[str, str]) -> str:
    return (row.get("姓", "") + row.get("名", "")).strip()


def collect_works_by_author(rows: list[dict[str, str]]) -> dict[str, list[Work]]:
    works_by_author: dict[str, list[Work]] = defaultdict(list)
    seen_by_author: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        if row.get("作品著作権フラグ", "").strip() != "なし":
            continue

        text_url = row.get("テキストファイルURL", "").strip()
        if not text_url:
            continue

        author = author_full_name(row)
        if not author:
            continue

        work_id = row.get("作品ID", "").strip()
        if not work_id or work_id in seen_by_author[author]:
            continue

        seen_by_author[author].add(work_id)
        works_by_author[author].append(
            Work(
                work_id=work_id,
                title=row.get("作品名", "").strip() or f"work_{work_id}",
                release_date=row.get("公開日", "").strip(),
                text_url=text_url,
            )
        )

    for author in works_by_author:
        works_by_author[author].sort(key=lambda w: (w.release_date, w.work_id), reverse=True)

    return works_by_author


def select_authors(
    works_by_author: dict[str, list[Work]],
    author_count: int,
    min_works: int,
    include_list: list[str] | None,
) -> list[str]:
    available = [(name, len(works)) for name, works in works_by_author.items() if len(works) >= min_works]
    available.sort(key=lambda item: (item[1], item[0]), reverse=True)

    if include_list:
        selected = [name for name in include_list if name in works_by_author and len(works_by_author[name]) >= min_works]
        already = set(selected)
        for name, _ in available:
            if len(selected) >= author_count:
                break
            if name in already:
                continue
            selected.append(name)
        return selected[:author_count]

    return [name for name, _ in available[:author_count]]


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp932", "shift_jis", "euc-jp"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def extract_text_from_payload(payload: bytes, source_url: str) -> str:
    if source_url.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            txt_members = [name for name in zf.namelist() if name.lower().endswith(".txt")]
            if not txt_members:
                raise ValueError(f"No .txt in zip: {source_url}")
            return decode_text(zf.read(txt_members[0]))
    return decode_text(payload)


def clean_aozora_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"《[^》]*》", "", text)
    text = re.sub(r"［＃[^］]*］", "", text)
    text = text.replace("｜", "")
    text = re.sub(r"^[-=]{20,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^(入力|校正|底本|公開|初出|翻訳|作成)[：:].*$", "", text, flags=re.MULTILINE)

    if "底本：" in text:
        text = text.split("底本：", 1)[0]

    marker = "-------------------------------------------------------"
    if marker in text:
        parts = text.split(marker)
        if len(parts) >= 3:
            text = "\n".join(parts[2:])

    lines = [ln.strip() for ln in text.split("\n")]
    lines = [
        ln
        for ln in lines
        if ln and not ln.startswith("入力：") and not ln.startswith("校正：") and not ln.startswith("青空文庫")
    ]

    text = "\n".join(lines)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[\t\u3000 ]+", " ", text)
    return text.strip()


def split_into_chunks(text: str, min_chars: int, max_chars: int, max_chunks: int) -> list[str]:
    if not text:
        return []

    sentences = re.split(r"(?<=[。！？])", text)
    chunks: list[str] = []
    buf = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        candidate = buf + sentence
        if len(candidate) <= max_chars:
            buf = candidate
            continue

        if len(buf) >= min_chars:
            chunks.append(buf)
            if len(chunks) >= max_chunks:
                return chunks
            buf = sentence
        else:
            long_text = candidate
            while len(long_text) > max_chars:
                chunks.append(long_text[:max_chars])
                if len(chunks) >= max_chunks:
                    return chunks
                long_text = long_text[max_chars:]
            buf = long_text

    if len(buf) >= min_chars and len(chunks) < max_chunks:
        chunks.append(buf)

    return chunks


def safe_author_dirname(author_name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", author_name)


def load_include_authors(path: str | None) -> list[str] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"author list file not found: {path}")

    names = [line.strip() for line in p.read_text(encoding="utf-8").splitlines()]
    names = [n for n in names if n and not n.startswith("#")]
    return names or None


def build_corpus(
    output_csv: Path,
    stats_json: Path,
    raw_dir: Path,
    metadata_zip: Path,
    author_count: int,
    min_works: int,
    works_per_author: int,
    target_chunks_per_author: int,
    min_chars: int,
    max_chars: int,
    max_chunks_per_work: int,
    min_used_works: int,
    force_download: bool,
    include_authors: list[str] | None,
) -> None:
    rows = read_metadata_rows(metadata_zip)
    works_by_author = collect_works_by_author(rows)
    selected_authors = select_authors(
        works_by_author=works_by_author,
        author_count=author_count,
        min_works=min_works,
        include_list=include_authors,
    )

    if len(selected_authors) < author_count:
        eprint(
            f"Warning: requested {author_count} authors but selected {len(selected_authors)} "
            f"(min_works={min_works})."
        )

    corpus_rows: list[dict[str, str]] = []
    stats: dict[str, dict[str, int]] = {}

    for author_name in selected_authors:
        works = works_by_author[author_name][:works_per_author]
        eprint(f"[{author_name}] available works: {len(works_by_author[author_name])} / selected: {len(works)}")

        stats[author_name] = {
            "available_works": len(works_by_author[author_name]),
            "selected_works": len(works),
            "used_works": 0,
            "chunks": 0,
            "chars": 0,
        }

        author_raw_dir = raw_dir / safe_author_dirname(author_name)
        author_raw_dir.mkdir(parents=True, exist_ok=True)

        for work in works:
            local_text = author_raw_dir / f"{work.work_id}.txt"

            try:
                if local_text.exists() and not force_download:
                    clean_text = clean_aozora_text(local_text.read_text(encoding="utf-8"))
                else:
                    payload = fetch_bytes(work.text_url)
                    raw_text = extract_text_from_payload(payload, work.text_url)
                    clean_text = clean_aozora_text(raw_text)
                local_text.write_text(clean_text, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                eprint(f"[warn] {author_name} work={work.work_id} download/parse failed: {exc}")
                continue

            chunks = split_into_chunks(
                clean_text,
                min_chars=min_chars,
                max_chars=max_chars,
                max_chunks=max_chunks_per_work,
            )
            if not chunks:
                continue

            stats[author_name]["used_works"] += 1
            for idx, chunk in enumerate(chunks, start=1):
                corpus_rows.append(
                    {
                        "label": author_name,
                        "text": chunk,
                        "work_id": work.work_id,
                        "work_title": work.title,
                        "sample_id": f"{work.work_id}_{idx:04d}",
                    }
                )
                stats[author_name]["chunks"] += 1
                stats[author_name]["chars"] += len(chunk)

            if (
                stats[author_name]["chunks"] >= target_chunks_per_author
                and stats[author_name]["used_works"] >= min_used_works
            ):
                break

        if stats[author_name]["used_works"] < min_used_works:
            eprint(
                f"[warn] {author_name}: used works {stats[author_name]['used_works']} "
                f"< min_used_works {min_used_works}"
            )

    if not corpus_rows:
        raise RuntimeError("Corpus generation failed: no rows created")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "text", "work_id", "work_title", "sample_id"])
        writer.writeheader()
        writer.writerows(corpus_rows)

    label_counts = Counter(row["label"] for row in corpus_rows)

    summary = {
        "total_samples": len(corpus_rows),
        "author_count": len(selected_authors),
        "selected_authors": selected_authors,
        "label_distribution": dict(sorted(label_counts.items(), key=lambda item: item[1], reverse=True)),
        "authors": stats,
        "params": {
            "author_count": author_count,
            "min_works": min_works,
            "works_per_author": works_per_author,
            "target_chunks_per_author": target_chunks_per_author,
            "min_chars": min_chars,
            "max_chars": max_chars,
            "max_chunks_per_work": max_chunks_per_work,
            "min_used_works": min_used_works,
        },
        "source": {
            "metadata_zip": str(metadata_zip),
            "metadata_url": METADATA_URL,
        },
    }

    stats_json.parent.mkdir(parents=True, exist_ok=True)
    stats_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    eprint(f"Saved corpus: {output_csv} ({len(corpus_rows)} samples)")
    eprint(f"Saved stats:  {stats_json}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build corpus from Aozora Bunko")
    parser.add_argument("--author-count", type=int, default=100)
    parser.add_argument("--min-works", type=int, default=30)
    parser.add_argument("--works-per-author", type=int, default=160)
    parser.add_argument("--target-chunks-per-author", type=int, default=90)
    parser.add_argument("--min-chars", type=int, default=100)
    parser.add_argument("--max-chars", type=int, default=320)
    parser.add_argument("--max-chunks-per-work", type=int, default=80)
    parser.add_argument("--min-used-works", type=int, default=10)
    parser.add_argument("--include-authors-file", default="")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-metadata", action="store_true")

    parser.add_argument("--metadata-zip", default="data/corpus/list_person_all_extended_utf8.zip")
    parser.add_argument("--output-csv", default="data/corpus/aozora_corpus.csv")
    parser.add_argument("--stats-json", default="data/corpus/aozora_corpus_stats.json")
    parser.add_argument("--raw-dir", default="data/raw")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    metadata_zip = ensure_metadata_zip(Path(args.metadata_zip), force=args.force_metadata)
    include_authors = load_include_authors(args.include_authors_file or None)

    build_corpus(
        output_csv=Path(args.output_csv),
        stats_json=Path(args.stats_json),
        raw_dir=Path(args.raw_dir),
        metadata_zip=metadata_zip,
        author_count=args.author_count,
        min_works=args.min_works,
        works_per_author=args.works_per_author,
        target_chunks_per_author=args.target_chunks_per_author,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        max_chunks_per_work=args.max_chunks_per_work,
        min_used_works=args.min_used_works,
        force_download=args.force_download,
        include_authors=include_authors,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
