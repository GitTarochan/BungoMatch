"use strict";

const THEMES = [
  {
    id: "rain_station",
    label: "雨の夜、駅へ向かう五分間",
    prompt:
      "雨の夜に駅へ向かう短い道のりを描いてください。見えた風景と、心の動きを必ず入れてください。",
    min: 180,
    target: 260,
    max: 380,
  },
  {
    id: "letter_friend",
    label: "久しぶりの友人への手紙",
    prompt:
      "長く会っていない友人に近況を伝える文章を書いてください。事実だけでなく、ためらいや本音も混ぜてください。",
    min: 200,
    target: 290,
    max: 420,
  },
  {
    id: "old_memory",
    label: "子どもの頃の失敗の回想",
    prompt:
      "幼いころの小さな失敗をひとつ選び、当時の感情と今の視点を行き来するように書いてください。",
    min: 180,
    target: 250,
    max: 380,
  },
  {
    id: "city_mystery",
    label: "街で見つけた小さな不思議",
    prompt:
      "日常の街角で見つけた奇妙な出来事を描いてください。説明しすぎず、読後に余韻が残る形を意識してください。",
    min: 190,
    target: 280,
    max: 400,
  },
];

const TOP10_FAMOUS_AUTHORS = [
  "夏目漱石",
  "太宰治",
  "芥川竜之介",
  "宮沢賢治",
  "森鴎外",
  "樋口一葉",
  "谷崎潤一郎",
  "江戸川乱歩",
  "与謝野晶子",
  "泉鏡花",
];

const AUTHOR_FALLBACK_META = {
  "夏目漱石": {
    label: "理知と皮肉の観察者",
    comment: "理知的な観察と、感情を少し距離を置いて眺める語りが強く出ています。",
    representative_work: "坊っちやん",
    aozora_url: "https://www.aozora.gr.jp/cards/000148/card50420.html",
  },
  "太宰治": {
    label: "自己告白の揺らぎ",
    comment: "自己告白的な文体が目立ちます。弱さを隠さず差し出す語り口です。",
    representative_work: "人間失格",
    aozora_url: "https://www.aozora.gr.jp/cards/000035/card301.html",
  },
  "芥川竜之介": {
    label: "冷静な描写と陰影",
    comment: "場面描写が先に立ち、人物の内面が遅れて浮かぶ構図が目立ちます。",
    representative_work: "羅生門",
    aozora_url: "https://www.aozora.gr.jp/cards/000879/card127.html",
  },
  "芥川龍之介": {
    label: "冷静な描写と陰影",
    comment: "場面描写が先に立ち、人物の内面が遅れて浮かぶ構図が目立ちます。",
    representative_work: "羅生門",
    aozora_url: "https://www.aozora.gr.jp/cards/000879/card127.html",
  },
  "宮沢賢治": {
    label: "自然と宇宙の感応",
    comment: "自然現象と心情を重ねる、詩的で澄んだ運びが出ています。",
    representative_work: "銀河鉄道の夜",
    aozora_url: "https://www.aozora.gr.jp/cards/000081/card46322.html",
  },
  "森鴎外": {
    label: "理性と感情の緊張",
    comment: "論理性のある運びの中に、抑えた情念がにじむ語りです。",
    representative_work: "舞姫",
    aozora_url: "https://www.aozora.gr.jp/cards/000129/card682.html",
  },
  "樋口一葉": {
    label: "余情と気配の細工",
    comment: "語尾の余情と人物の気配をにじませる運びが強めです。",
    representative_work: "たけくらべ",
    aozora_url: "https://www.aozora.gr.jp/cards/000064/card389.html",
  },
  "谷崎潤一郎": {
    label: "美意識と官能の配列",
    comment: "美の対象を執拗に見つめるような精密な描写が近いです。",
    representative_work: "痴人の愛",
    aozora_url: "https://www.aozora.gr.jp/cards/001383/card58093.html",
  },
  "江戸川乱歩": {
    label: "怪奇と論理の二重奏",
    comment: "異様な空気の演出と、謎を追う運びの両方が現れています。",
    representative_work: "怪人二十面相",
    aozora_url: "https://www.aozora.gr.jp/cards/001779/card57228.html",
  },
  "与謝野晶子": {
    label: "感情の直截な熱量",
    comment: "感情を率直に押し出す、勢いのある言葉選びが目立ちます。",
    representative_work: "みだれ髪",
    aozora_url: "https://www.aozora.gr.jp/cards/000885/card51307.html",
  },
  "泉鏡花": {
    label: "幻想と雅語の陰影",
    comment: "現実と幻想の境界をぼかす、装飾的で濃密な語りです。",
    representative_work: "高野聖",
    aozora_url: "https://www.aozora.gr.jp/cards/000050/card43466.html",
  },
};

const DEFAULT_STOPWORDS = [
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
];

const MODEL_PATH = "./models/author_style_web_model.json";
const LENGTH_CLASSES = ["is-short", "is-good", "is-long"];

const formEl = document.getElementById("judge-form");
const themeSelectEl = document.getElementById("theme-select");
const themePromptEl = document.getElementById("theme-prompt");
const rangeTextEl = document.getElementById("range-text");
const userTextEl = document.getElementById("user-text");
const charCountEl = document.getElementById("char-count");
const lengthStatusEl = document.getElementById("length-status");
const judgeButtonEl = document.getElementById("judge-button");
const resultPanelEl = document.getElementById("result-panel");
const topAuthorEl = document.getElementById("top-author");
const topScoreEl = document.getElementById("top-score");
const topWorkEl = document.getElementById("top-work");
const topLinkEl = document.getElementById("top-link");
const topCommentEl = document.getElementById("top-comment");
const rankingListEl = document.getElementById("ranking-list");
const analysisTextEl = document.getElementById("analysis-text");
const modelStatusEl = document.getElementById("model-status");
const authorPreviewListEl = document.getElementById("author-preview-list");
const suspenseStateEl = document.getElementById("suspense-state");
const suspenseMeterEl = document.getElementById("suspense-meter");

let currentTheme = THEMES[0];
let modelBundle = null;
let modelReady = false;
let isJudging = false;

init();

async function init() {
  renderThemeOptions();
  applyTheme(currentTheme.id);
  renderAuthorPreview(getFallbackPreviewAuthors());

  themeSelectEl.addEventListener("change", () => {
    applyTheme(themeSelectEl.value);
    updateLengthState();
  });

  userTextEl.addEventListener("input", updateLengthState);
  formEl.addEventListener("submit", handleSubmit);

  updateLengthState();
  await loadTrainedModel();
}

function renderThemeOptions() {
  THEMES.forEach((theme) => {
    const option = document.createElement("option");
    option.value = theme.id;
    option.textContent = theme.label;
    themeSelectEl.append(option);
  });
}

function getAuthorMeta(authorName) {
  if (modelBundle && modelBundle.authors && modelBundle.authors[authorName]) {
    return modelBundle.authors[authorName];
  }
  return AUTHOR_FALLBACK_META[authorName] || {
    label: "",
    comment: "",
    representative_work: "",
    aozora_url: "",
  };
}

function applyTheme(themeId) {
  const theme = THEMES.find((item) => item.id === themeId);
  if (!theme) {
    return;
  }

  currentTheme = theme;
  themeSelectEl.value = theme.id;
  themePromptEl.textContent = theme.prompt;
  rangeTextEl.textContent = `${theme.min}〜${theme.max}字（目安 ${theme.target}字）`;
}

async function loadTrainedModel() {
  setModelStatus("学習済みモデルを読み込み中...", "");

  try {
    const response = await fetch(MODEL_PATH, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`model fetch failed: ${response.status}`);
    }

    const payload = await response.json();
    validateModelPayload(payload);

    modelBundle = payload;
    modelReady = true;

    const classCount = payload.classifier.classes.length;
    const accuracy = payload.evaluation && typeof payload.evaluation.accuracy === "number"
      ? `${(payload.evaluation.accuracy * 100).toFixed(1)}%`
      : "-";
    setModelStatus(`学習済みモデル読込済み（著者数: ${classCount} / 評価Accuracy: ${accuracy}）`, "ready");
    renderAuthorPreview(getPreviewAuthors(payload));
  } catch (error) {
    modelReady = false;
    console.error(error);
    setModelStatus("モデル読込に失敗しました。モデル生成後に再読み込みしてください。", "error");
  }

  updateLengthState();
}

function validateModelPayload(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("invalid model payload");
  }

  if (!payload.vectorizer || !payload.classifier) {
    throw new Error("missing vectorizer/classifier");
  }

  const hasRequiredVectorizer =
    payload.vectorizer.vocabulary &&
    Array.isArray(payload.vectorizer.idf) &&
    Array.isArray(payload.vectorizer.ngram_range);

  const hasRequiredClassifier =
    Array.isArray(payload.classifier.classes) &&
    Array.isArray(payload.classifier.coef) &&
    Array.isArray(payload.classifier.intercept);

  if (!hasRequiredVectorizer || !hasRequiredClassifier) {
    throw new Error("model payload schema mismatch");
  }
}

function setModelStatus(text, variant) {
  modelStatusEl.textContent = text;
  modelStatusEl.classList.remove("is-ready", "is-error");

  if (variant === "ready") {
    modelStatusEl.classList.add("is-ready");
  }
  if (variant === "error") {
    modelStatusEl.classList.add("is-error");
  }
}


function getFallbackPreviewAuthors() {
  return TOP10_FAMOUS_AUTHORS.map((name) => {
    const meta = AUTHOR_FALLBACK_META[name] || {};
    return {
      name,
      representativeWork: meta.representative_work || "代表作情報なし",
      aozoraUrl: meta.aozora_url || "",
    };
  });
}

function getPreviewAuthors(payload) {
  const classes = payload?.classifier?.classes || [];
  if (!classes.length) {
    return getFallbackPreviewAuthors();
  }

  const orderMap = new Map(TOP10_FAMOUS_AUTHORS.map((name, idx) => [name, idx]));
  const items = classes
    .map((name) => {
      const meta = getAuthorMeta(name);
      const fallback = AUTHOR_FALLBACK_META[name] || {};
      return {
        name,
        representativeWork: fallback.representative_work || meta.representative_work || "代表作情報なし",
        aozoraUrl: fallback.aozora_url || meta.aozora_url || "",
      };
    })
    .sort((a, b) => {
      const left = orderMap.has(a.name) ? orderMap.get(a.name) : Number.MAX_SAFE_INTEGER;
      const right = orderMap.has(b.name) ? orderMap.get(b.name) : Number.MAX_SAFE_INTEGER;
      return left - right || a.name.localeCompare(b.name, "ja");
    });

  return items;
}

function renderAuthorPreview(items) {
  authorPreviewListEl.replaceChildren();

  items.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "author-preview-item";
    card.style.setProperty("--delay", `${index * 40}ms`);

    const name = document.createElement("p");
    name.className = "author-preview-name";
    name.textContent = item.name;

    const work = document.createElement("p");
    work.className = "author-preview-work";
    work.textContent = `代表作: ${item.representativeWork}`;

    card.append(name, work);

    if (item.aozoraUrl) {
      const link = document.createElement("a");
      link.className = "author-preview-link";
      link.href = item.aozoraUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "青空文庫";
      card.append(link);
    }

    authorPreviewListEl.append(card);
  });
}

async function handleSubmit(event) {
  event.preventDefault();
  if (!modelReady || !modelBundle || isJudging) {
    return;
  }

  const length = getCharLength(userTextEl.value);
  if (!isLengthValid(length)) {
    return;
  }

  const preprocessedText = preprocessText(userTextEl.value);
  const tfidfEntries = vectorizeToTfidf(preprocessedText, modelBundle.vectorizer);
  if (!tfidfEntries.length) {
    analysisTextEl.textContent = "入力文から既知特徴量を抽出できませんでした。語彙を増やして再試行してください。";
    return;
  }

  const ranking = classifyLogistic(tfidfEntries, modelBundle.classifier);
  if (!ranking.length) {
    return;
  }

  const topThree = ranking.slice(0, 3);

  setJudgingState(true);
  try {
    await wait(980);
    renderResult(topThree, ranking, {
      rawText: userTextEl.value,
      preprocessedLength: preprocessedText.length,
      featureCount: tfidfEntries.length,
      tfidfEntries,
    });
  } finally {
    setJudgingState(false);
  }
}

function setJudgingState(active) {
  isJudging = active;
  formEl.classList.toggle("is-judging", active);

  if (active) {
    judgeButtonEl.textContent = "文豪を召喚中";
    suspenseStateEl.hidden = false;
    suspenseMeterEl.hidden = false;
    suspenseStateEl.classList.add("is-active");
  } else {
    judgeButtonEl.textContent = "文豪を判定する";
    suspenseStateEl.hidden = true;
    suspenseMeterEl.hidden = true;
    suspenseStateEl.classList.remove("is-active");
  }

  updateLengthState();
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function getStopwords() {
  const modelStopwords = modelBundle?.preprocessing?.stopwords;
  if (Array.isArray(modelStopwords) && modelStopwords.length) {
    return modelStopwords;
  }
  return DEFAULT_STOPWORDS;
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildStopwordRegex(stopwords) {
  const words = [...new Set(stopwords)]
    .map((word) => String(word).trim())
    .filter((word) => word.length > 0)
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp);

  if (!words.length) {
    return null;
  }

  return new RegExp(words.join("|"), "g");
}

function preprocessText(text) {
  let normalized = text.normalize("NFKC").replace(/\s+/g, "");
  normalized = normalized.replace(/[「」『』（）()［］【】〈〉《》〔〕…・。、，．！？!?ー〜～:：;；"'`]/g, "");
  normalized = normalized.replace(/[0-9０-９]+/g, "");

  const stopwordRegex = buildStopwordRegex(getStopwords());
  if (stopwordRegex) {
    normalized = normalized.replace(stopwordRegex, "");
  }

  return normalized;
}

function vectorizeToTfidf(text, vectorizer) {
  const counts = new Map();
  const [minN, maxN] = vectorizer.ngram_range;
  const vocabulary = vectorizer.vocabulary;
  const idf = vectorizer.idf;

  for (let size = minN; size <= maxN; size += 1) {
    if (text.length < size) {
      continue;
    }

    for (let index = 0; index <= text.length - size; index += 1) {
      const token = text.slice(index, index + size);
      const rawIndex = vocabulary[token];
      if (rawIndex === undefined) {
        continue;
      }

      const tokenIndex = Number(rawIndex);
      counts.set(tokenIndex, (counts.get(tokenIndex) || 0) + 1);
    }
  }

  if (!counts.size) {
    return [];
  }

  const entries = [];
  let normSquare = 0;

  counts.forEach((tf, tokenIndex) => {
    const value = tf * (idf[tokenIndex] || 1);
    entries.push([tokenIndex, value]);
    normSquare += value * value;
  });

  const norm = Math.sqrt(normSquare) || 1;
  return entries.map(([tokenIndex, value]) => [tokenIndex, value / norm]);
}

function classifyLogistic(tfidfEntries, classifier) {
  const classes = classifier.classes;
  const coef = classifier.coef;
  const intercept = classifier.intercept;
  const logits = intercept.map((bias) => bias);

  tfidfEntries.forEach(([tokenIndex, value]) => {
    for (let classIndex = 0; classIndex < classes.length; classIndex += 1) {
      const weights = coef[classIndex];
      if (!weights || weights[tokenIndex] === undefined) {
        continue;
      }
      logits[classIndex] += weights[tokenIndex] * value;
    }
  });

  const maxLogit = Math.max(...logits);
  const expValues = logits.map((logit) => Math.exp(logit - maxLogit));
  const expSum = expValues.reduce((sum, value) => sum + value, 0) || 1;

  return classes
    .map((authorName, classIndex) => {
      const probability = expValues[classIndex] / expSum;
      const meta = getAuthorMeta(authorName);
      return {
        name: authorName,
        percent: probability * 100,
        probability,
        classIndex,
        label: meta.label || "",
        comment: meta.comment || `${authorName}の語りに近い文体傾向が見られます。`,
        representativeWork: meta.representative_work || "",
        aozoraUrl: meta.aozora_url || "",
      };
    })
    .sort((a, b) => b.percent - a.percent);
}

function renderResult(topThree, ranking, pipeline) {
  const winner = topThree[0];
  topAuthorEl.textContent = winner.name;
  topScoreEl.textContent = `推定確率 ${winner.percent.toFixed(1)}%`;
  topCommentEl.textContent = winner.comment;

  topWorkEl.textContent = winner.representativeWork ? `代表作: ${winner.representativeWork}` : "代表作: 情報なし";
  if (winner.aozoraUrl) {
    topLinkEl.hidden = false;
    topLinkEl.href = winner.aozoraUrl;
  } else {
    topLinkEl.hidden = true;
    topLinkEl.removeAttribute("href");
  }

  renderRankingItems(topThree);
  const analysisText = buildAnalysisText(ranking, pipeline);
  analysisTextEl.textContent = analysisText;
  resultPanelEl.hidden = false;
  resultPanelEl.classList.remove("is-reveal");
  void resultPanelEl.offsetWidth;
  resultPanelEl.classList.add("is-reveal");
  resultPanelEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderRankingItems(items) {
  rankingListEl.replaceChildren();
  items.forEach((item, index) => {
    const row = document.createElement("article");
    row.className = "ranking-item";
    row.style.animationDelay = `${index * 110}ms`;

    const head = document.createElement("div");
    head.className = "ranking-head";

    const name = document.createElement("p");
    name.className = "ranking-name";
    name.textContent = `${index + 1}位 ${item.name}`;

    const score = document.createElement("p");
    score.className = "ranking-score";
    score.textContent = `${item.percent.toFixed(1)}%`;

    head.append(name, score);

    const bar = document.createElement("div");
    bar.className = "bar";

    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.min(100, Math.max(2, item.percent))}%`;

    const work = document.createElement("p");
    work.className = "ranking-meta";
    work.textContent = item.representativeWork ? `代表作: ${item.representativeWork}` : "代表作: 情報なし";

    row.append(head, bar, work);
    bar.append(fill);

    if (item.aozoraUrl) {
      const link = document.createElement("a");
      link.className = "ranking-link";
      link.href = item.aozoraUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "青空文庫ページ";
      row.append(link);
    }

    rankingListEl.append(row);
  });
}

function buildAnalysisText(ranking, pipeline) {
  const top = ranking[0];
  const second = ranking[1];
  const margin = second ? top.percent - second.percent : top.percent;
  const topTokens = pickTopContributingTokens(top.classIndex, pipeline.tfidfEntries, 4);
  const rhythm = summarizeWritingRhythm(pipeline.rawText || "");

  const reasonByTokens = topTokens.length
    ? `「${topTokens.join("」「")}」のような言い回しが、この文豪らしさとして強く反応しました。`
    : "言い回しの特徴が全体に散らばっていました。";

  const reasonByRhythm = `文の運びは${rhythm.tempoText}（${rhythm.sentenceCount}文 / 1文平均${rhythm.avgSentenceLength.toFixed(1)}字）で、${rhythm.perspectiveText}。${rhythm.emotionText}。`;

  const reasonByComparison = second
    ? describeGap(top.name, second.name, margin)
    : `${top.name}に最も近い傾向が出ました。`;

  return `判定理由は2つです。1) ${reasonByRhythm} 2) ${reasonByTokens} さらに、2位との比較では${reasonByComparison} 助詞などの共通語は除外して、内容に関わる言い回しを中心に比べています。`;
}

function summarizeWritingRhythm(text) {
  const normalized = String(text || "").replace(/\s+/g, "");
  const sentences = normalized
    .split(/[。！？!?]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  const sentenceCount = Math.max(1, sentences.length);
  const charLength = Math.max(1, getCharLength(normalized));
  const avgSentenceLength = charLength / sentenceCount;

  let tempoText = "中くらいの長さの文が続くバランス型";
  if (avgSentenceLength < 18) {
    tempoText = "短めの文を重ねるテンポ型";
  } else if (avgSentenceLength >= 34) {
    tempoText = "長めの文でじっくり描写する型";
  }

  const firstPersonCount = (normalized.match(/私|わたし|僕|ぼく|俺|おれ|わし/g) || []).length;
  const perspectiveText =
    firstPersonCount >= 2
      ? "一人称が多く、内面に寄った語り口です"
      : "一人称は控えめで、情景や出来事を見せる語り口です";

  const punctCount = (String(text || "").match(/[！？!?]/g) || []).length;
  let emotionText = "感情表現は抑えめで、落ち着いた印象です";
  if (punctCount >= 3) {
    emotionText = "感嘆符・疑問符が多く、感情の波がはっきりしています";
  } else if (punctCount >= 1) {
    emotionText = "要所で感情を強める書き方が見られます";
  }

  return {
    sentenceCount,
    avgSentenceLength,
    tempoText,
    perspectiveText,
    emotionText,
  };
}

function describeGap(topName, secondName, margin) {
  if (margin >= 15) {
    return `${secondName}より${margin.toFixed(1)}pt高く、${topName}らしさがはっきり出ています。`;
  }
  if (margin >= 6) {
    return `${secondName}より${margin.toFixed(1)}pt高く、${topName}がやや優勢です。`;
  }
  return `${secondName}との差は${margin.toFixed(1)}ptで僅差です。`;
}

function pickTopContributingTokens(classIndex, tfidfEntries, limit) {
  if (!modelBundle) {
    return [];
  }

  const coef = modelBundle.classifier.coef[classIndex];
  const indexToToken = modelBundle.vectorizer.index_to_token || [];
  const contributions = [];

  tfidfEntries.forEach(([tokenIndex, tfidfValue]) => {
    const weight = coef[tokenIndex] || 0;
    const contribution = tfidfValue * weight;
    if (contribution <= 0) {
      return;
    }

    const token = indexToToken[tokenIndex];
    if (!token) {
      return;
    }

    contributions.push({ token, contribution });
  });

  contributions.sort((a, b) => b.contribution - a.contribution);

  const picked = [];
  contributions.forEach((item) => {
    if (!/^[ぁ-んァ-ヶ一-龯]{2,3}$/.test(item.token)) {
      return;
    }
    if (picked.length >= limit || picked.includes(item.token)) {
      return;
    }
    picked.push(item.token);
  });

  return picked;
}

function isLengthValid(length) {
  return length >= currentTheme.min && length <= currentTheme.max;
}

function updateLengthState() {
  const length = getCharLength(userTextEl.value);
  charCountEl.textContent = `${length}字`;

  lengthStatusEl.classList.remove(...LENGTH_CLASSES);

  let lengthOk = false;
  if (length < currentTheme.min) {
    lengthStatusEl.classList.add("is-short");
    lengthStatusEl.textContent = `あと${currentTheme.min - length}字で判定可能`;
  } else if (length > currentTheme.max) {
    lengthStatusEl.classList.add("is-long");
    lengthStatusEl.textContent = `${length - currentTheme.max}字オーバー`;
  } else {
    lengthStatusEl.classList.add("is-good");
    lengthStatusEl.textContent = `判定可能（目安 ${currentTheme.target}字）`;
    lengthOk = true;
  }

  judgeButtonEl.disabled = !(lengthOk && modelReady) || isJudging;
}

function getCharLength(text) {
  return [...text.replace(/\s+/g, "")].length;
}
