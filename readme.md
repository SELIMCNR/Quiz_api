# Quiz API (FastAPI)

Ultra hafif, on-the-fly soru üreten, 100 kategori x 50 dil x 10,000 soru (kategori başına) destekleyen quiz API.

## Özellikler

- 100 kategori (Category 1 .. Category 100)
- 50 dil (tr, en, de, fr, es, ... toplam 50 kod)
- Zorluk: easy, medium, hard
- Modlar:
  - mixed: rastgele kategori/dil/zorluk kombinasyonu içinde sampling
  - category: belirli kategoriden pagination ile çekme (offset+amount)
- Deterministic ID ve doğru cevap seçimi (seed ile tekrarlanabilir)
- CORS, health ve meta uç noktaları

## Hızlı Başlangıç

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# Docs: http://127.0.0.1:8000/docs
```
