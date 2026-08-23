# Sözleşme Analiz Asistanı

Sözleşmelerinizi yükleyin; içeriğini özetleyelim, dikkat etmeniz gereken maddeleri
işaretleyelim, aklınıza takılan soruları yanıtlayalım ve isterseniz birden fazla
sözleşmeyi karşılaştıralım.

Tamamen yerel çalışır: hiçbir belge internete ya da üçüncü bir servise
gönderilmez, her şey kendi bilgisayarınızda kalır.

> **Not:** Bu araç sözleşme inceleme sürecini desteklemek için geliştirilmiştir.
> Ürettiği analiz ve yanıtlar profesyonel hukuki danışmanlığın yerini tutmaz.

## Özellikler

- **Sözleşme yükleme** — PDF, DOCX, TXT ve Markdown (.md) dosyaları desteklenir,
  birden fazla dosya aynı anda yüklenebilir.
- **Otomatik özet** — taraflar, tutar, tarihler ve önemli yükümlülükler
  otomatik çıkarılır.
- **Risk analizi** — sık karşılaşılan riskli ifadeler ve eksik olabilecek
  standart maddeler taranır; bulgular önem derecesine göre (kritik / yüksek /
  orta / düşük) işaretlenir. Kontrol listesi sözleşmenin türüne göre uyarlanır
  (örn. bir boşanma protokolünde ticari sözleşmelere özgü konular aranmaz).
- **Kaynaklı sohbet** — sözleşmeyle ilgili sorularınıza, hangi maddeye
  dayandığını gösteren yanıtlar alırsınız.
- **Karşılaştırma** — 2-5 sözleşmeyi seçip ortak konularda (fesih, sorumluluk,
  ödeme vb.) yan yana karşılaştırabilirsiniz.
- **Nasıl Çalışır sayfası** — uygulama içi kullanım kılavuzu ve SSS.

## Teknoloji

| Katman | Teknoloji |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI (Python), SQLite |
| Dil modeli | [Ollama](https://ollama.com) — tamamen yerel, ücretsiz, API anahtarı gerekmez |
| Arama | Anahtar kelime + anlamsal arama birleşimi (opsiyonel `sentence-transformers`) |

## Kurulum

### Ön koşullar

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com) kurulu ve çalışır durumda

```bash
ollama pull qwen2.5:7b
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 8090 --reload
```

Anlamsal (dense) aramayı etkinleştirmek isterseniz (opsiyonel, ~2 GB indirir):

```bash
pip install -r requirements-embeddings.txt
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev -- --port 3000
```

Uygulama `http://localhost:3000` adresinde açılır.

## Proje yapısı

```
backend/
  app/
    ingest/      # Dosya ayrıştırma ve maddelere bölme
    llm/         # Ollama istemcisi ve promptlar
    rag/         # Arama motoru (anahtar kelime + anlamsal)
    routers/     # API uç noktaları
    services/    # Risk analizi, soru-cevap, karşılaştırma mantığı
frontend/
  app/           # Sayfalar (sözleşmeler, sohbet, karşılaştır, nasıl çalışır)
  components/    # Paylaşılan arayüz bileşenleri
  lib/           # API istemcisi ve yardımcı fonksiyonlar
```

## Gizlilik

Yüklenen belgeler, çıkarılan analizler ve sohbet geçmişi yalnızca yerel
`backend/data/` klasöründeki SQLite veritabanında saklanır; bu klasör
depoya (repository) dahil değildir ve hiçbir veri dışarı gönderilmez.
