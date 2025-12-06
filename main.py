# main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import random

app = FastAPI(
    title="Quiz API",
    description="On-the-fly generated quiz questions with multi-language support",
    version="1.0.0",
)

# CORS (uygulaman için domain ekleyebilirsin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prod'da kısıtla
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model
class QuizQuestion(BaseModel):
    id: str = Field(..., example="cat_0001_en_easy_42")
    category: str
    difficulty: str
    language: str
    text: str
    options: List[str]
    correctAnswerIndex: int
    correctAnswer: str

# 100 kategori üretimi (programatik)
CATEGORIES: List[str] = [f"Category {i+1}" for i in range(100)]

# 50 dil (ISO benzeri kısa kodlar + açıklamalar)
LANGUAGES: List[str] = [
    "tr","en","de","fr","es","it","pt","ru","nl","sv",
    "no","da","fi","pl","cs","sk","hu","ro","bg","sr",
    "hr","sl","el","uk","ar","fa","he","hi","bn","ur",
    "ta","te","ml","kn","gu","mr","pa","zh","ja","ko",
    "id","ms","vi","th","la","et","lt","is","ga","mk"
]

DIFFICULTIES = ["easy", "medium", "hard"]

# Metin üretimi (dil uyarlamalı, basit ama tutarlı)
def localized_text(category: str, difficulty: str, index: int, lang: str) -> str:
    if lang == "tr":
        return f"{category} kategorisinden {difficulty} seviye soru {index+1}"
    if lang == "en":
        return f"{category} {difficulty} level question {index+1}"
    if lang == "de":
        return f"{category} {difficulty} Stufe Frage {index+1}"
    if lang == "fr":
        return f"Question de niveau {difficulty} dans {category} {index+1}"
    if lang == "es":
        return f"Pregunta de nivel {difficulty} en {category} {index+1}"
    # Diğer diller için basit bir fallback
    return f"{category} ({lang}) {difficulty} question {index+1}"

# Şıklar (dile göre basit varyasyon)
def localized_options(lang: str) -> List[str]:
    base = ["A", "B", "C", "D"]
    if lang == "tr":
        return ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"]
    if lang == "en":
        return ["Option A", "Option B", "Option C", "Option D"]
    if lang == "de":
        return ["Option A", "Option B", "Option C", "Option D"]
    if lang == "fr":
        return ["Option A", "Option B", "Option C", "Option D"]
    if lang == "es":
        return ["Opción A", "Opción B", "Opción C", "Opción D"]
    return base

# Deterministic ID (kategori, dil, zorluk ve index'e göre)
def make_id(cat_idx: int, lang: str, difficulty: str, q_index: int) -> str:
    return f"cat_{cat_idx:03d}_{lang}_{difficulty}_{q_index:04d}"

# Tek soru üretimi (deterministic veya random)
def build_question(cat_idx: int, lang: str, difficulty: str, q_index: int, rng: random.Random) -> QuizQuestion:
    category = CATEGORIES[cat_idx]
    options = localized_options(lang)
    # deterministik doğru cevap için RNG seed sabitleme (stabil sonuçlar için)
    # Seed: kategori + dil + zorluk + index
    seed_val = (cat_idx + 1) * 1_000_000 + LANGUAGES.index(lang) * 10_000 + DIFFICULTIES.index(difficulty) * 1_000 + q_index
    local_rng = random.Random(seed_val)
    correct_idx = local_rng.randint(0, 3)
    return QuizQuestion(
        id=make_id(cat_idx, lang, difficulty, q_index),
        category=category,
        difficulty=difficulty,
        language=lang,
        text=localized_text(category, difficulty, q_index, lang),
        options=options,
        correctAnswerIndex=correct_idx,
        correctAnswer=options[correct_idx],
    )

# Toplam soru sayısı
TOTAL_PER_CATEGORY = 10_000
TOTAL_QUESTIONS = len(CATEGORIES) * TOTAL_PER_CATEGORY  # 1,000,000

# Sağlık ve meta
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/meta")
def meta():
    return {
        "categories": len(CATEGORIES),
        "languages": len(LANGUAGES),
        "difficulties": DIFFICULTIES,
        "total_per_category": TOTAL_PER_CATEGORY,
        "total_questions": TOTAL_QUESTIONS,
    }

# Ana endpoint: kategoriye göre veya rastgele
@app.get("/quiz/questions", response_model=List[QuizQuestion])
def get_questions(
    category: Optional[str] = Query(None, description="Kategori adı (opsiyonel, örn. 'Category 1')"),
    language: str = Query("tr", description="Dil kodu (örn. tr, en, de...)"),
    difficulty: Optional[str] = Query(None, description="Zorluk (easy, medium, hard)"),
    amount: int = Query(10, ge=1, le=100, description="Kaç soru getirilsin (1-100)"),
    mode: str = Query("mixed", description="mixed veya category"),
    offset: int = Query(0, ge=0, description="Kategori modunda başlangıç indeksi (pagination)"),
    seed: Optional[int] = Query(None, description="Karışık modda deterministic seçim için seed"),
):
    # Dil doğrulama
    if language not in LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    # Zorluk ayarla (yoksa karışık)
    if difficulty and difficulty not in DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"Unsupported difficulty: {difficulty}")

    rng = random.Random(seed) if seed is not None else random.Random()

    # category modunda: belirli kategoriden pagination ile seç
    if mode == "category":
        if not category:
            raise HTTPException(status_code=400, detail="category mode requires 'category' parameter")
        if category not in CATEGORIES:
            raise HTTPException(status_code=404, detail=f"Category not found: {category}")

        cat_idx = CATEGORIES.index(category)
        # pagination sınırları
        start = offset
        end = min(offset + amount, TOTAL_PER_CATEGORY)
        if start >= TOTAL_PER_CATEGORY:
            return []

        # difficulty yoksa karışık atama
        diffs = [difficulty] if difficulty else DIFFICULTIES

        items: List[QuizQuestion] = []
        for i in range(start, end):
            diff = rng.choice(diffs)
            items.append(build_question(cat_idx, language, diff, i, rng))
        return items

    # mixed modunda: 100 farklı kategori/dil/zorluk karışık sampling
    elif mode == "mixed":
        items: List[QuizQuestion] = []
        for _ in range(amount):
            cat_idx = rng.randint(0, len(CATEGORIES) - 1)
            diff = difficulty if difficulty else rng.choice(DIFFICULTIES)
            q_index = rng.randint(0, TOTAL_PER_CATEGORY - 1)
            items.append(build_question(cat_idx, language, diff, q_index, rng))
        return items

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported mode: {mode}")