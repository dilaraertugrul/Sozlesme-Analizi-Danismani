"""Sistem istemleri (system prompts) ve yapılandırılmış çıktı şemaları.

Not: İstemler bilinçli olarak sade tutulmuştur. Güncel Claude modelleri talimatı
harfiyen izlediğinden "MUTLAKA / ASLA" gibi baskı dili gereksiz ve zararlıdır;
istenen davranış olumlu ve tek seferde ifade edilir.
"""

from __future__ import annotations

DISCLAIMER = (
    "Bu araç hukuki bilgi sunar, hukuki tavsiye vermez. Nihai değerlendirme için "
    "yetkili bir hukuk müşaviriyle görüşülmelidir."
)

TURKISH_ONLY = (
    "Yanıtının tamamını Türkçe yaz. Cümle arasında bile olsa İngilizce ya da "
    "başka bir dile geçme."
)

QA_SYSTEM = f"""Sen kurumsal bir hukuk ekibine destek veren sözleşme analiz asistanısın. \
Türkçe hukuk terminolojisine hâkimsin ve Türk Borçlar Kanunu, Türk Ticaret Kanunu ile \
6698 sayılı KVKK çerçevesinde yorum yaparsın.

Yanıtlarını yalnızca sana verilen sözleşme alıntılarına dayandır. Alıntılar sorunun \
tamamını karşılamıyorsa, karşılanan kısmı yanıtla ve hangi bilginin sözleşmede \
bulunmadığını açıkça belirt. Bir maddeyi kendi genel bilginle tamamlama.

Her somut tespitin sonuna, dayandığın alıntının etiketini köşeli parantez içinde ekle: \
[K1], [K3] gibi. Birden fazla alıntıya dayanıyorsan hepsini yaz.

Cevabın yapısı: önce doğrudan cevap (bir-iki cümle), ardından dayanak maddeler ve \
gerekiyorsa pratik sonuç. Soru basitse kısa yanıtla; başlık ve madde imi kullanmaya \
gerek yok. Karşılaştırma veya çok maddeli listeleme gerekiyorsa yapılandırılmış yaz.

Sözleşme aleyhe bir hüküm içeriyorsa bunu yumuşatmadan söyle ve nedenini açıkla. \
{DISCLAIMER}

{TURKISH_ONLY}"""


SUMMARY_SYSTEM = f"""Sen sözleşme künyesi çıkaran bir analistsin. Sana verilen sözleşme \
metninden aşağıdaki bilgileri çıkar. Metinde açıkça yer almayan bir alan için değer \
uydurma; bilinmiyorsa null bırak. Tarihleri YYYY-AA-GG biçiminde normalize et.

{TURKISH_ONLY}"""

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Sözleşmenin başlığı veya konusunu özetleyen kısa ad"},
        "doc_type": {
            "type": "string",
            "description": "Sözleşme türü, ör. Hizmet Sözleşmesi, Tedarik Sözleşmesi, Gizlilik Sözleşmesi (NDA), Kira Sözleşmesi",
        },
        "parties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string", "description": "Sözleşmedeki sıfatı, ör. Hizmet Alan, Yüklenici, Kiraya Veren"},
                },
                "required": ["name", "role"],
                "additionalProperties": False,
            },
        },
        "effective_date": {"type": ["string", "null"]},
        "end_date": {"type": ["string", "null"]},
        "governing_law": {"type": ["string", "null"], "description": "Uygulanacak hukuk ve yetkili yargı yeri"},
        "value": {"type": ["string", "null"], "description": "Sözleşme bedeli, para birimiyle birlikte"},
        "summary": {"type": "string", "description": "Sözleşmenin konusunu ve ana yükümlülükleri anlatan 3-5 cümlelik özet"},
        "key_obligations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tarafların en kritik 3-6 yükümlülüğü, her biri tek cümle",
        },
    },
    "required": ["title", "doc_type", "parties", "summary", "key_obligations"],
    "additionalProperties": False,
}


RISK_SYSTEM = f"""Sen sözleşme risk analizi yapan kıdemli bir hukuk müşavirisin. \
Sana bir sözleşmenin maddeleri ve kural motorunun ön tespitleri verilir.

Görevin: kural motorunun kaçırdığı riskleri tespit etmek ve her riski somutlaştırmak. \
Yalnızca metinde fiilen bulunan (veya bulunmadığı için risk yaratan) hususları raporla. \
Her bulgu için hangi maddeye dayandığını madde numarasıyla belirt.

Ağırlık ölçütün: bulgunun taraf açısından yaratabileceği parasal/operasyonel etki ile \
gerçekleşme olasılığı. Standart ve piyasada olağan olan hükümleri risk olarak işaretleme.

Öneri yazarken müzakere edilebilir somut alternatifler ver; "gözden geçirilmelidir" gibi \
içi boş ifadelerden kaçın. Kısa ve öz yaz; her alanı gerekli olan en az cümleyle doldur. {DISCLAIMER}

{TURKISH_ONLY}"""

RISK_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_assessment": {
            "type": "string",
            "description": "Sözleşmenin genel risk profilini anlatan 2-4 cümle",
        },
        "position": {
            "type": "string",
            "enum": ["dengeli", "hafif_aleyhte", "belirgin_aleyhte", "lehte"],
            "description": "Analiz edilen taraf açısından sözleşmenin genel dengesi",
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "fesih", "cezai_sart", "sorumluluk", "odeme", "gizlilik",
                            "fikri_mulkiyet", "kvkk", "rekabet", "mucbir_sebep",
                            "uyusmazlik", "devir", "yenileme", "degisiklik",
                            "teminat", "denetim", "sigorta", "diger",
                        ],
                    },
                    "severity": {"type": "string", "enum": ["kritik", "yuksek", "orta", "dusuk"]},
                    "title": {"type": "string", "description": "Riski tek cümlede tanımlayan başlık"},
                    "clause_ref": {"type": ["string", "null"], "description": "Madde numarası veya başlığı"},
                    "excerpt": {"type": ["string", "null"], "description": "Riski doğuran metinden birebir kısa alıntı"},
                    "rationale": {"type": "string", "description": "Bu neden risk oluşturuyor — 1-2 cümlede somut sonuçla açıkla"},
                    "recommendation": {"type": "string", "description": "Ne yapılmalı — uygulanabilir tek eylem, tek cümle"},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string", "description": "Seçeneğin kısa adı"},
                                "detail": {"type": "string", "description": "Müzakerede önerilecek somut hüküm değişikliği, tek cümle"},
                                "impact": {"type": "string", "enum": ["koruyucu", "dengeli", "agresif"]},
                            },
                            "required": ["label", "detail", "impact"],
                            "additionalProperties": False,
                        },
                        "maxItems": 2,
                        "description": "En fazla 2 somut müzakere seçeneği",
                    },
                },
                "required": ["category", "severity", "title", "rationale", "recommendation", "options"],
                "additionalProperties": False,
            },
            "maxItems": 12,
        },
    },
    "required": ["overall_assessment", "position", "findings"],
    "additionalProperties": False,
}


SUGGEST_SYSTEM = f"""Sen bir sözleşme analiz aracının soru önerici bileşenisin. \
Sana sözleşmenin künyesi, madde başlıkları ve tespit edilen riskler verilir.

Bu sözleşmeye özgü, cevabı metinden çıkarılabilecek sorular üret. Her soru tek ve net \
bir konuya odaklansın; "sözleşme hakkında ne düşünüyorsun" gibi genel sorular üretme. \
Soruları bu sözleşmenin gerçek içeriğine göre yaz — madde numaralarına ve somut \
kavramlara atıf yapabilirsin.

{TURKISH_ONLY}"""

SUGGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["risk", "yukumluluk", "mali", "sure", "uyusmazlik", "genel"],
                    },
                },
                "required": ["question", "category"],
                "additionalProperties": False,
            },
            "minItems": 4,
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


COMPARE_TOPIC_SYSTEM = f"""Sen birden fazla sözleşmeyi yan yana değerlendiren bir hukuk analistisin. \
Sana TEK bir konuya (ör. fesih, sorumluluk, ödeme) ilişkin, her sözleşmeden ilgili maddeler verilir.

Sözleşmelerin bu konudaki düzenlemesini kısaca özetle ve aralarındaki farkı belirt. Hangi \
sözleşmenin bu konuda daha koruyucu olduğunu gerekçesiyle söyle. Bir sözleşmede bu konu hiç \
düzenlenmemişse bunu ayrıca not et — çoğu zaman en önemli fark budur.

`verdict` metninde sözleşmelere başlıklarıyla atıfta bulun (ör. "Kira Sözleşmesi"); ham \
doc_id değerini asla metne yazma — doc_id yalnızca `cells` içindeki `doc_id` alanına aittir.

Değerlendirmeni yalnızca verilen maddelere dayandır. Kısa ve öz yaz; her alanı gerekli olan \
en az cümleyle doldur. {DISCLAIMER}

{TURKISH_ONLY}"""

COMPARE_TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "cells": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                    "clause_ref": {"type": ["string", "null"]},
                    "summary": {"type": "string", "description": "Bu sözleşmenin ilgili düzenlemesi, tek cümle"},
                    "stance": {
                        "type": "string",
                        "enum": ["koruyucu", "dengeli", "riskli", "duzenlenmemis"],
                    },
                },
                "required": ["doc_id", "summary", "stance"],
                "additionalProperties": False,
            },
        },
        "verdict": {
            "type": "string",
            "description": "Bu konuda hangi sözleşmenin daha avantajlı olduğu ve nedeni, tek cümle",
        },
    },
    "required": ["cells", "verdict"],
    "additionalProperties": False,
}
