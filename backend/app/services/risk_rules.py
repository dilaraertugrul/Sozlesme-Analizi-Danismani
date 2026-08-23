"""Kural tabanlı risk kataloğu.

İki tür bulgu üretilir:

* **Varlık riski** — maddede geçen bir ifade tek başına risk taşır
  (ör. "tek taraflı ve tazminatsız fesih", "sınırsız sorumluluk").
* **Yokluk riski** — sözleşmede hiç bulunmayan bir düzenlemenin eksikliği risk
  yaratır (ör. mücbir sebep maddesi yok, sorumluluk üst sınırı yok).

Kural motoru deterministiktir ve API anahtarı olmadan da çalışır; LLM katmanı
bunun üzerine bağlam yorumu ve müzakere önerisi ekler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SEVERITY_WEIGHT = {"kritik": 10.0, "yuksek": 6.0, "orta": 3.0, "dusuk": 1.0, "bilgi": 0.0}

SEVERITY_LABEL = {
    "kritik": "Kritik",
    "yuksek": "Yüksek",
    "orta": "Orta",
    "dusuk": "Düşük",
    "bilgi": "Bilgi",
}

CATEGORY_LABEL = {
    "fesih": "Fesih ve Sona Erme",
    "cezai_sart": "Cezai Şart ve Tazminat",
    "sorumluluk": "Sorumluluk Sınırı",
    "odeme": "Ödeme ve Mali Koşullar",
    "gizlilik": "Gizlilik",
    "fikri_mulkiyet": "Fikri Mülkiyet",
    "kvkk": "Kişisel Verilerin Korunması",
    "rekabet": "Rekabet Yasağı",
    "mucbir_sebep": "Mücbir Sebep",
    "uyusmazlik": "Uyuşmazlık Çözümü",
    "devir": "Devir ve Temlik",
    "yenileme": "Süre ve Yenileme",
    "degisiklik": "Tek Taraflı Değişiklik",
    "teminat": "Teminat ve Garanti",
    "denetim": "Denetim ve Raporlama",
    "sigorta": "Sigorta",
}


@dataclass
class Option:
    label: str
    detail: str
    impact: str  # "koruyucu" | "dengeli" | "agresif"


@dataclass
class Rule:
    id: str
    category: str
    title: str
    severity: str
    patterns: list[str]
    rationale: str
    recommendation: str
    options: list[Option] = field(default_factory=list)
    # Yokluk riski tanımı (opsiyonel)
    presence_patterns: list[str] = field(default_factory=list)
    absence_title: str | None = None
    absence_severity: str | None = None
    absence_rationale: str | None = None
    absence_recommendation: str | None = None

    _compiled: list[re.Pattern] = field(default_factory=list, repr=False)
    _compiled_presence: list[re.Pattern] = field(default_factory=list, repr=False)

    def compile(self) -> "Rule":
        self._compiled = [re.compile(p) for p in self.patterns]
        self._compiled_presence = [re.compile(p) for p in self.presence_patterns]
        return self

    def match(self, lowered_text: str) -> str | None:
        """Eşleşen ilk desenin yakaladığı metin parçasını döndürür."""
        for pattern in self._compiled:
            if m := pattern.search(lowered_text):
                return m.group(0)
        return None

    def is_present(self, lowered_text: str) -> bool:
        return any(p.search(lowered_text) for p in self._compiled_presence)


def _opt(label: str, detail: str, impact: str) -> Option:
    return Option(label=label, detail=detail, impact=impact)


RULES: list[Rule] = [
    Rule(
        id="fesih-tek-tarafli-tazminatsiz",
        category="fesih",
        title="Tek taraflı ve tazminatsız fesih yetkisi",
        severity="kritik",
        patterns=[
            r"tek\s*tarafl[ıi][^.]{0,140}(fesh|fesih)",
            r"(fesh|fesih)[^.]{0,140}tek\s*tarafl[ıi]",
            r"(herhangi\s*bir\s*)?(gerekçe|sebep|neden)\s*(göstermeksizin|belirtmeksizin|olmaksızın)[^.]{0,120}(fesh|fesih)",
            r"(fesh|fesih)[^.]{0,120}(tazminat\s*ödemeksizin|tazminatsız|bedel\s*ödemeksizin)",
        ],
        rationale=(
            "Karşı tarafa gerekçe göstermeden ve tazminat ödemeden sözleşmeyi sona erdirme "
            "hakkı tanınması, yapılan yatırımın ve planlanan gelirin tek taraflı riske "
            "atılması anlamına gelir."
        ),
        recommendation=(
            "Fesih hakkını haklı sebeplerle sınırlandırın; sebepsiz fesih kalacaksa asgari "
            "ihbar süresi ve yatırım telafi bedeli ekleyin."
        ),
        options=[
            _opt("Haklı sebeple sınırlandır", "Fesih yalnızca sayılan haklı sebeplerin varlığında kullanılabilsin; sebepsiz fesih maddeden çıkarılsın.", "koruyucu"),
            _opt("İhbar süresi + telafi bedeli", "Sebepsiz fesih korunsun ancak 60–90 gün yazılı ihbar ve kalan dönem bedelinin belirli bir oranı ödensin.", "dengeli"),
            _opt("Karşılıklı hale getir", "Aynı fesih hakkı simetrik biçimde her iki tarafa da tanınsın.", "dengeli"),
        ],
        presence_patterns=[r"fesh|fesih|sona\s*er"],
        absence_title="Fesih koşulları düzenlenmemiş",
        absence_severity="yuksek",
        absence_rationale="Sözleşmede fesih usulü ve sebepleri düzenlenmediğinden, sona erme yalnızca genel kanun hükümlerine bırakılmıştır; bu, uyuşmazlık halinde öngörülemezlik yaratır.",
        absence_recommendation="Haklı sebeple fesih, ihbarlı fesih ve fesih sonrası tasfiye/iade yükümlülüklerini açıkça düzenleyen bir madde ekleyin.",
    ),
    Rule(
        id="fesih-ihbar-suresi-kisa",
        category="fesih",
        title="Kısa fesih ihbar süresi",
        severity="orta",
        patterns=[
            r"(\b[1-9]\b|\b1[0-4]\b)\s*(gün|gu?n)\s*(önceden|önce)?[^.]{0,60}(ihbar|bildirim)[^.]{0,60}(fesh|fesih)",
            r"(fesh|fesih)[^.]{0,80}(\b[1-9]\b|\b1[0-4]\b)\s*gün\s*(önceden|önce)",
        ],
        rationale="Çok kısa ihbar süresi, hizmetin/tedarikin ikamesini bulmaya ve personel-stok planlamasına zaman bırakmaz.",
        recommendation="İhbar süresini sözleşmenin süresi ve operasyonel bağımlılık düzeyiyle orantılı olacak şekilde (tipik olarak 30–90 gün) uzatın.",
        options=[
            _opt("30 güne çıkar", "Standart ticari uygulamaya uygun asgari geçiş süresi.", "dengeli"),
            _opt("90 güne çıkar", "Operasyonel bağımlılığın yüksek olduğu tedarik/hizmet ilişkilerinde tercih edilir.", "koruyucu"),
        ],
    ),
    Rule(
        id="sorumluluk-sinirsiz",
        category="sorumluluk",
        title="Sınırsız sorumluluk üstlenimi",
        severity="kritik",
        patterns=[
            r"s[ıi]n[ıi]rs[ıi]z\s*(olarak\s*)?sorumlu",
            r"her\s*t[üu]rl[üu]\s*zarar[^.]{0,80}sorumlu",
            r"do[ğg]rudan\s*(ve|,)?\s*dolayl[ıi]\s*(t[üu]m\s*)?zarar",
            r"t[üu]m\s*zarar\s*ve\s*ziyan[^.]{0,60}tazmin",
        ],
        rationale=(
            "Sorumluluğun üst sınırı belirlenmediğinde, sözleşmeden elde edilen gelirin "
            "kat kat üzerinde bir tazminat riski doğar; dolaylı zararların da kapsama "
            "alınması bu riski öngörülemez hale getirir."
        ),
        recommendation="Toplam sorumluluğu belirli bir tavana bağlayın ve dolaylı/netice zararlarını (kâr kaybı, iş kaybı, itibar zararı) kapsam dışı bırakın.",
        options=[
            _opt("Yıllık bedelle tavanla", "Toplam sorumluluk, fesihten önceki 12 ayda ödenen toplam bedeli aşmasın.", "koruyucu"),
            _opt("Dolaylı zararları hariç tut", "Kâr kaybı, veri kaybı ve netice zararları açıkça kapsam dışında bırakılsın.", "koruyucu"),
            _opt("Kademeli tavan", "Genel ihlaller için 12 aylık bedel, gizlilik/KVKK ihlalleri için ayrı ve daha yüksek bir tavan tanımlansın.", "dengeli"),
        ],
        presence_patterns=[r"sorumlulu[ğg]un?\s*(üst\s*)?s[ıi]n[ıi]r|sorumluluk\s*tavan|azami\s*sorumlu"],
        absence_title="Sorumluluk üst sınırı belirlenmemiş",
        absence_severity="yuksek",
        absence_rationale="Sözleşmede toplam sorumluluğu sınırlayan bir tavan bulunmadığından, tek bir ihlal sözleşme değerinin çok üzerinde tazminat talebine yol açabilir.",
        absence_recommendation="Toplam sorumluluğu, ilgili dönemde ödenen bedelle sınırlayan bir üst sınır maddesi ekleyin.",
    ),
    Rule(
        id="cezai-sart-orantisiz",
        category="cezai_sart",
        title="Orantısız veya tek taraflı cezai şart",
        severity="yuksek",
        patterns=[
            r"cezai\s*[şs]art",
            r"(ceza|tazminat)\s*olarak[^.]{0,80}(%|y[üu]zde)\s*\d{2,}",
            r"g[üu]nl[üu]k[^.]{0,40}(ceza|cezai)",
        ],
        rationale="Cezai şartın yalnızca bir tarafa yüklenmesi veya asıl edimle orantısız olması, ihlalin ekonomik sonucunu fahiş hale getirir.",
        recommendation="Cezai şartı karşılıklı hale getirin, toplam tavan belirleyin ve fiilî zararı aşan kısmın mahkemece indirilebileceğini not edin.",
        options=[
            _opt("Toplam tavan koy", "Cezai şart toplamı, sözleşme bedelinin belirli bir yüzdesini (ör. %10) aşamasın.", "koruyucu"),
            _opt("Karşılıklı hale getir", "Aynı yükümlülük ihlalinde her iki taraf için simetrik ceza öngörülsün.", "dengeli"),
            _opt("Önce ihtar şartı", "Ceza ancak yazılı ihtar ve verilen düzeltme süresinin sonuçsuz kalması halinde işlesin.", "dengeli"),
        ],
    ),
    Rule(
        id="odeme-vade-uzun",
        category="odeme",
        title="Uzun ödeme vadesi",
        severity="orta",
        patterns=[
            r"(\b(9\d|1\d\d)\b)\s*g[üu]n[^.]{0,60}(ödeme|öde|fatura|vade)",
            r"(ödeme|fatura)[^.]{0,60}(\b(9\d|1\d\d)\b)\s*g[üu]n",
        ],
        rationale="90 günü aşan vadeler işletme sermayesi üzerinde baskı yaratır ve karşı tarafın ödeme güçlüğüne girmesi halinde tahsilat riskini büyütür.",
        recommendation="Vadeyi 30–60 güne çekin veya gecikme faizi ve teminat mekanizmasıyla dengeleyin.",
        options=[
            _opt("Vadeyi kısalt", "Fatura tarihinden itibaren 30 gün içinde ödeme.", "koruyucu"),
            _opt("Gecikme faizi ekle", "Vade korunsun ancak gecikmede ticari işlerde uygulanan avans faizi işlesin.", "dengeli"),
        ],
    ),
    Rule(
        id="odeme-tek-tarafli-fiyat-degisikligi",
        category="odeme",
        title="Tek taraflı fiyat/bedel değiştirme yetkisi",
        severity="yuksek",
        patterns=[
            r"(bedel|fiyat|[üu]cret)[^.]{0,120}tek\s*tarafl[ıi][^.]{0,60}(de[ğg]i[şs]tir|art[ıi]r|güncelle)",
            r"tek\s*tarafl[ıi][^.]{0,80}(fiyat|bedel|[üu]cret)[^.]{0,60}(de[ğg]i[şs]tir|art[ıi]r|güncelle)",
        ],
        rationale="Bedelin karşı tarafça tek taraflı değiştirilebilmesi, maliyet öngörülebilirliğini ortadan kaldırır.",
        recommendation="Fiyat artışını objektif bir endekse (TÜFE/ÜFE) ve yıllık azami orana bağlayın; artış halinde fesih hakkı tanıyın.",
        options=[
            _opt("Endekse bağla", "Artış yıllık TÜFE oranını aşamasın ve yılda en fazla bir kez uygulansın.", "koruyucu"),
            _opt("Onay şartı", "Her fiyat değişikliği karşı tarafın yazılı onayına tabi olsun.", "koruyucu"),
            _opt("Artışta fesih hakkı", "Belirlenen eşiği aşan artışlarda cezasız fesih hakkı doğsun.", "dengeli"),
        ],
    ),
    Rule(
        id="degisiklik-tek-tarafli",
        category="degisiklik",
        title="Sözleşme şartlarında tek taraflı değişiklik yetkisi",
        severity="yuksek",
        patterns=[
            r"tek\s*tarafl[ıi][^.]{0,140}(de[ğg]i[şs]iklik|de[ğg]i[şs]tirme|tadil)",
            r"(de[ğg]i[şs]iklik|tadil)[^.]{0,100}tek\s*tarafl[ıi]",
            r"([şs]artlar|h[üu]k[üu]mler)[^.]{0,100}(diledi[ğg]i\s*zaman|her\s*zaman)[^.]{0,60}de[ğg]i[şs]tir",
        ],
        rationale="Bir tarafın sözleşme hükümlerini tek başına değiştirebilmesi, müzakere edilen dengeyi sonradan bozabilir.",
        recommendation="Değişikliklerin yalnızca karşılıklı imzalı yazılı ek protokolle yapılabileceğini düzenleyin.",
        options=[
            _opt("Yazılı ek protokol şartı", "Her değişiklik iki tarafın imzasını taşıyan yazılı ek ile geçerli olsun.", "koruyucu"),
            _opt("Bildirim + itiraz hakkı", "Tek taraflı değişiklik 30 gün önceden bildirilsin; itiraz halinde cezasız fesih hakkı doğsun.", "dengeli"),
        ],
    ),
    Rule(
        id="gizlilik-suresiz-veya-eksik",
        category="gizlilik",
        title="Gizlilik yükümlülüğünün kapsamı",
        severity="orta",
        patterns=[
            r"s[üu]resiz[^.]{0,80}gizli",
            r"gizli[^.]{0,80}s[üu]resiz",
        ],
        rationale="Süresiz gizlilik yükümlülüğü, ticari sır niteliğini yitirmiş bilgiler için dahi belirsiz süreli sorumluluk yaratır.",
        recommendation="Gizlilik süresini sözleşme sonrası belirli bir dönemle (tipik olarak 3–5 yıl) sınırlayın; ticari sırlar için istisna tanımlayın.",
        options=[
            _opt("5 yıl ile sınırla", "Sözleşmenin sona ermesinden itibaren 5 yıl.", "dengeli"),
            _opt("Ticari sır istisnası", "Genel bilgiler için süreli, ticari sır niteliğindekiler için süresiz koruma.", "koruyucu"),
        ],
        presence_patterns=[r"gizli|s[ıi]r\b|confidential|ifşa\s*etme"],
        absence_title="Gizlilik maddesi bulunmuyor",
        absence_severity="yuksek",
        absence_rationale="Sözleşmede gizlilik yükümlülüğü düzenlenmediğinden, paylaşılan ticari ve teknik bilgilerin korunması sözleşmesel güvenceden yoksundur.",
        absence_recommendation="Gizli bilginin tanımı, istisnaları, koruma süresi ve ihlal sonuçlarını içeren bir gizlilik maddesi ekleyin.",
    ),
    Rule(
        id="fikri-mulkiyet-devri",
        category="fikri_mulkiyet",
        title="Fikri mülkiyet haklarının kayıtsız devri",
        severity="yuksek",
        patterns=[
            r"(t[üu]m|b[üu]t[üu]n)\s*(fikri|s[ıi]nai)[^.]{0,120}(devred|devir|ait\s*olacak)",
            r"(mali\s*haklar|telif)[^.]{0,120}(s[ıi]n[ıi]rs[ıi]z|s[üu]resiz|bedelsiz)[^.]{0,60}devr",
            r"(fikri\s*m[üu]lkiyet|telif)[^.]{0,100}bedelsiz",
        ],
        rationale="Arka plan (background) fikri mülkiyetin ayrıştırılmadan devri, önceden geliştirilmiş kendi teknolojinizin de karşı tarafa geçmesine yol açabilir.",
        recommendation="Arka plan ve ön plan (foreground) fikri mülkiyeti ayırın; kendi altyapınız için devir yerine kullanım lisansı verin.",
        options=[
            _opt("Arka planı ayır", "Sözleşme öncesi geliştirilen her şey devredende kalsın; yalnızca teslim edilen çıktı devredilsin.", "koruyucu"),
            _opt("Devir yerine lisans", "Münhasır olmayan, süresiz kullanım lisansı verilsin; mülkiyet sizde kalsın.", "koruyucu"),
            _opt("Bedele bağla", "Devir korunsun ancak ayrı ve açıkça belirlenmiş bir devir bedeli kararlaştırılsın.", "dengeli"),
        ],
        presence_patterns=[r"fikri\s*m[üu]lkiyet|telif|patent|marka|mali\s*haklar"],
        absence_title="Fikri mülkiyet düzenlemesi yok",
        absence_severity="orta",
        absence_rationale="Üretilen çıktıların mülkiyeti ve kullanım hakları düzenlenmediğinden, teslim sonrası hak sahipliği tartışmalı hale gelebilir.",
        absence_recommendation="Çıktıların mülkiyeti, kullanım lisansı ve üçüncü kişi haklarına ilişkin taahhütleri düzenleyen bir madde ekleyin.",
    ),
    Rule(
        id="kvkk-eksik",
        category="kvkk",
        title="Kişisel veri işleme düzenlemesi",
        severity="yuksek",
        patterns=[
            r"ki[şs]isel\s*veri[^.]{0,120}(s[ıi]n[ıi]rs[ıi]z|serbest[çc]e|diledi[ğg]i)",
            r"ki[şs]isel\s*veri[^.]{0,100}[üu][çc][üu]nc[üu]\s*ki[şs]i[^.]{0,80}(aktar|payla[şs])",
        ],
        rationale="Kişisel verilerin sınırsız işlenmesi veya üçüncü kişilere serbestçe aktarılması, 6698 sayılı KVKK kapsamında veri sorumlusu açısından idari para cezası riski doğurur.",
        recommendation="Veri işleme amacını, hukuki sebebini, aktarım koşullarını ve saklama süresini sınırlandırın; taraflar arası veri işleme sözleşmesi ekleyin.",
        options=[
            _opt("Veri işleyen sözleşmesi ekle", "KVKK m.12 uyarınca teknik ve idari tedbirleri düzenleyen ayrı bir ek sözleşme.", "koruyucu"),
            _opt("Aktarımı onaya bağla", "Yurt içi/yurt dışı her aktarım öncesi yazılı onay şartı.", "koruyucu"),
            _opt("Saklama süresi tanımla", "Amaç ortadan kalktığında verilerin imhası ve imha tutanağı yükümlülüğü.", "dengeli"),
        ],
        presence_patterns=[r"ki[şs]isel\s*veri|kvkk|6698|veri\s*sorumlusu|veri\s*i[şs]leyen"],
        absence_title="KVKK / kişisel veri maddesi bulunmuyor",
        absence_severity="orta",
        absence_rationale="Sözleşme kapsamında kişisel veri işlenmesi söz konusuysa, KVKK yükümlülüklerinin taraflar arasında paylaşımı düzenlenmemiştir.",
        absence_recommendation="Veri sorumlusu/veri işleyen sıfatlarını, güvenlik tedbirlerini ve ihlal bildirim süresini düzenleyen bir madde ekleyin.",
    ),
    Rule(
        id="rekabet-yasagi-genis",
        category="rekabet",
        title="Geniş kapsamlı rekabet yasağı",
        severity="yuksek",
        patterns=[
            r"rekabet\s*(etmeme|yasa[ğg][ıi])",
            r"rakip[^.]{0,100}(çal[ıi][şs]|faaliyet)[^.]{0,60}(yasak|edemez)",
        ],
        rationale="Coğrafi alan, süre ve faaliyet konusu bakımından sınırlandırılmamış rekabet yasağı, TBK m.445 uyarınca aşırı sayılıp hâkim tarafından sınırlandırılabilir; ayrıca ticari hareket alanını daraltır.",
        recommendation="Yasağı süre (azami 2 yıl), coğrafi alan ve somut faaliyet konusu bakımından sınırlayın; karşılığında bedel öngörün.",
        options=[
            _opt("Üç boyutta sınırla", "Süre, yer ve konu bakımından açık sınırlar tanımlansın.", "koruyucu"),
            _opt("Karşılık bedeli ekle", "Yasak süresince ödenecek bir bedel kararlaştırılsın.", "dengeli"),
            _opt("Müşteri çekmeme ile değiştir", "Genel rekabet yasağı yerine yalnızca müşteri/personel ayartmama yükümlülüğü.", "dengeli"),
        ],
    ),
    Rule(
        id="mucbir-sebep-eksik",
        category="mucbir_sebep",
        title="Mücbir sebep düzenlemesi",
        severity="orta",
        patterns=[r"m[üu]cbir\s*sebep[^.]{0,120}(kabul\s*edilmez|say[ıi]lmaz|ge[çc]erli\s*de[ğg]il)"],
        rationale="Mücbir sebebin sözleşmeden dışlanması, deprem/salgın/idari yasak gibi kontrol dışı olaylarda dahi temerrüt sorumluluğu doğurur.",
        recommendation="Mücbir sebep hallerini örnekleyerek tanımlayın; bildirim süresi, askıya alma ve uzun süren mücbir sebepte fesih hakkını düzenleyin.",
        options=[
            _opt("Standart mücbir sebep maddesi", "Tanım + bildirim + askıya alma + 60 günü aşarsa cezasız fesih.", "dengeli"),
        ],
        presence_patterns=[r"m[üu]cbir\s*sebep|force\s*majeure|beklenmeyen\s*hal"],
        absence_title="Mücbir sebep maddesi bulunmuyor",
        absence_severity="orta",
        absence_rationale="Tarafların kontrolü dışındaki olaylarda yükümlülüklerin akıbeti düzenlenmediğinden, ifa imkânsızlığı halinde temerrüt tartışması doğabilir.",
        absence_recommendation="Mücbir sebep hallerini, bildirim usulünü ve uzun süreli mücbir sebepte fesih hakkını düzenleyen bir madde ekleyin.",
    ),
    Rule(
        id="uyusmazlik-yabanci-yetki",
        category="uyusmazlik",
        title="Yabancı hukuk veya yabancı mahkeme yetkisi",
        severity="orta",
        patterns=[
            r"(yetkili\s*mahkeme|yarg[ıi]\s*yetkisi)[^.]{0,100}(londra|new\s*york|singapur|isvi[çc]re|zurich|paris|dubai)",
            r"(uygulanacak\s*hukuk|tabi\s*olacak)[^.]{0,100}(ingiliz|isvi[çc]re|new\s*york|amerika)",
        ],
        rationale="Yabancı hukuk ve yabancı yargı yeri, uyuşmazlık halinde maliyeti ve süreyi ciddi ölçüde artırır; icra edilebilirlik sorunları doğurabilir.",
        recommendation="Türk hukuku ve Türkiye'de bir yargı yeri kararlaştırın; alternatif olarak Türkiye'de tahkim öngörün.",
        options=[
            _opt("Türk hukuku + yerel mahkeme", "Uygulanacak hukuk Türk hukuku, yetkili mahkeme İstanbul (Merkez) mahkemeleri.", "koruyucu"),
            _opt("İstanbul tahkimi", "ISTAC kuralları uyarınca İstanbul'da tahkim; hız ve gizlilik avantajı.", "dengeli"),
        ],
        presence_patterns=[r"yetkili\s*mahkeme|tahkim|uyu[şs]mazl[ıi]k|uygulanacak\s*hukuk"],
        absence_title="Uyuşmazlık çözümü ve yetkili merci belirlenmemiş",
        absence_severity="orta",
        absence_rationale="Yetkili mahkeme veya tahkim kaydı bulunmadığından, uyuşmazlık halinde yer ve usul belirsizliği ek maliyet yaratır.",
        absence_recommendation="Uygulanacak hukuku ve yetkili mahkeme/tahkim merciini açıkça belirleyen bir madde ekleyin.",
    ),
    Rule(
        id="devir-serbest",
        category="devir",
        title="Sözleşmenin onaysız devri",
        severity="orta",
        patterns=[
            r"(devred|temlik)[^.]{0,120}(onay[ıi]?\s*(olmaks[ıi]z[ıi]n|aranmaks[ıi]z[ıi]n)|serbest[çc]e)",
            r"(onay\s*almaks[ıi]z[ıi]n|izin\s*almaks[ıi]z[ıi]n)[^.]{0,80}(devred|temlik)",
        ],
        rationale="Karşı tarafın sözleşmeyi onayınız olmadan devredebilmesi, muhatabınızın bilmediğiniz (ve rakibiniz olabilecek) bir şirkete dönüşmesine yol açar.",
        recommendation="Devri yazılı onay şartına bağlayın; grup içi devirler için sınırlı bir istisna tanıyabilirsiniz.",
        options=[
            _opt("Yazılı onay şartı", "Her devir karşı tarafın önceden yazılı onayına tabi olsun.", "koruyucu"),
            _opt("Grup içi istisna", "Yalnızca aynı grup şirketlerine devir onaysız yapılabilsin, diğerleri onaya tabi olsun.", "dengeli"),
            _opt("Devirde fesih hakkı", "Kontrol değişikliği halinde cezasız fesih hakkı doğsun.", "dengeli"),
        ],
    ),
    Rule(
        id="otomatik-yenileme",
        category="yenileme",
        title="Otomatik yenileme (sessiz uzama)",
        severity="orta",
        patterns=[
            r"(kendili[ğg]inden|otomatik\s*olarak)[^.]{0,100}(yenilen|uzar|uzat[ıi]l)",
            r"(yenilen|uzar)[^.]{0,80}(itiraz\s*edilmedi[ğg]i|bildirimde\s*bulunulmad[ıi][ğg][ıi])",
        ],
        rationale="Sessiz uzama, ihbar penceresi kaçırıldığında istenmeyen bir dönem boyunca sözleşmeye bağlı kalınmasına neden olur.",
        recommendation="Yenilemeyi açık yazılı onaya bağlayın; korunacaksa ihbar penceresini uzun tutun ve takvim hatırlatıcısı kurun.",
        options=[
            _opt("Açık onay şartı", "Yenileme ancak iki tarafın yazılı teyidi ile gerçekleşsin.", "koruyucu"),
            _opt("İhbar penceresini uzat", "Yenilemeyi engellemek için 60 gün öncesine kadar bildirim yeterli olsun.", "dengeli"),
        ],
    ),
    Rule(
        id="teminat-agir",
        category="teminat",
        title="Ağır teminat / kesin teminat yükümlülüğü",
        severity="orta",
        patterns=[
            r"(kesin\s*teminat|teminat\s*mektubu)[^.]{0,100}(%|y[üu]zde)\s*(1[5-9]|[2-9]\d)",
            r"(nakit|banka)\s*teminat[^.]{0,80}(irat\s*kaydedil|gelir\s*kaydedil)",
        ],
        rationale="Yüksek oranlı ve ilk talepte ödenen teminat, ihtilaf halinde savunma imkânı doğmadan nakit çıkışına yol açar.",
        recommendation="Teminat oranını düşürün, kısmi iadeyi ifa aşamalarına bağlayın ve nakde çevirmeyi ihtar şartına tabi tutun.",
        options=[
            _opt("Oranı düşür", "Sözleşme bedelinin %6'sını aşmayan kesin teminat.", "koruyucu"),
            _opt("Kademeli iade", "Teslim aşamalarına bağlı olarak teminatın kademeli iadesi.", "dengeli"),
        ],
    ),
    Rule(
        id="sigorta-eksik",
        category="sigorta",
        title="Sigorta yükümlülüğü düzenlenmemiş",
        severity="dusuk",
        patterns=[],
        rationale="Mesleki sorumluluk / işveren sorumluluk sigortası öngörülmediğinde, zararın tahsil kabiliyeti karşı tarafın mali gücüne bağlı kalır.",
        recommendation="İş konusuna uygun asgari teminat tutarlı sigorta yaptırma ve poliçeyi ibraz etme yükümlülüğü ekleyin.",
        options=[
            _opt("Mesleki sorumluluk sigortası", "Asgari teminat tutarı belirlenerek poliçe ibrazı şart koşulsun.", "dengeli"),
        ],
        presence_patterns=[r"sigorta|poli[çc]e"],
        absence_title="Sigorta yükümlülüğü düzenlenmemiş",
        absence_severity="dusuk",
        absence_rationale="Sözleşmede sigorta yaptırma yükümlülüğü bulunmadığından, doğabilecek zararların karşılanması karşı tarafın ödeme gücüne bağlıdır.",
        absence_recommendation="İş konusuna uygun sigorta türü ve asgari teminat tutarını belirleyen bir madde ekleyin.",
    ),
    Rule(
        id="denetim-hakki-eksik",
        category="denetim",
        title="Denetim ve raporlama hakkı yok",
        severity="dusuk",
        patterns=[],
        rationale="Karşı tarafın yükümlülüklerine uyumunu doğrulama imkânı olmadan, ihlal ancak zarar doğduktan sonra fark edilir.",
        recommendation="Makul sıklıkta ve önceden bildirimli denetim hakkı ile periyodik raporlama yükümlülüğü ekleyin.",
        options=[
            _opt("Yıllık denetim hakkı", "Yılda bir kez, 10 gün önceden bildirimle yerinde denetim.", "dengeli"),
        ],
        presence_patterns=[r"denetim|deneti?le|rapor(la|lama)|audit"],
        absence_title="Denetim / raporlama hakkı bulunmuyor",
        absence_severity="dusuk",
        absence_rationale="Yükümlülüklere uyumun doğrulanmasına imkân veren bir mekanizma bulunmamaktadır.",
        absence_recommendation="Periyodik raporlama ve önceden bildirimli denetim hakkı tanıyan bir madde ekleyin.",
    ),
]

COMPILED_RULES = [rule.compile() for rule in RULES]


# --------------------------------------------------------------------------- #
# Sözleşme ailesi -> ilgili "yokluk" kategorileri
#
# Kural kataloğundaki 16 kategori ticari/iş sözleşmeleri (kira, hizmet, NDA,
# tedarik, iş sözleşmesi vb.) için tasarlandı. Aile hukuku belgeleri (boşanma
# protokolü, nafaka, velayet) veya sözleşme bile olmayan hukuki/akademik
# metinler için "gizlilik maddesi yok", "fikri mülkiyet düzenlemesi yok" gibi
# yokluk bulguları anlamsız ve yanıltıcı bir risk skoru üretir. Bu eşleme,
# hangi ailede hangi yokluk kategorilerinin gerçekten değerlendirilmesi
# gerektiğini belirler. "Varlık" (presence) bulguları — metinde fiilen riskli
# bir ifade geçtiği için üretilenler — bu filtrelemeden etkilenmez; gerçekten
# var olan riskli bir ifade her belge türünde raporlanmaya değer.
# --------------------------------------------------------------------------- #

FAMILY_ABSENCE_CATEGORIES: dict[str, set[str] | None] = {
    "ticari": None,  # None: tüm kategoriler uygulanır (varsayılan).
    "aile_hukuku": {"uyusmazlik"},
    "hukuki_metin": set(),
}

_FAMILY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aile_hukuku", re.compile(r"bo[şs]an|nafaka|velayet|evlat\s*edin|mal\s*rejimi|evlilik", re.IGNORECASE)),
    (
        "hukuki_metin",
        re.compile(
            r"makale|dergi|inceleme|tasar[ıi]s?\s*gerek[çc]e|hakemli|mevzuat|legal\s*analysis|kanun\s*gerek[çc]e",
            re.IGNORECASE,
        ),
    ),
]


def classify_family(doc_type: str | None) -> str:
    """Belge türü metninden kaba bir sözleşme ailesi çıkarır."""
    text = doc_type or ""
    for family, pattern in _FAMILY_PATTERNS:
        if pattern.search(text):
            return family
    return "ticari"


def applicable_absence_categories(doc_type: str | None) -> set[str] | None:
    """None: tüm kategoriler; aksi halde yalnızca bu kümedeki kategorilerde yokluk riski üretilir."""
    return FAMILY_ABSENCE_CATEGORIES.get(classify_family(doc_type), None)
