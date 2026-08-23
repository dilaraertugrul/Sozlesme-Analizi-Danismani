import { Scale, Upload, FileSearch, ShieldCheck, MessageSquareText, GitCompareArrows, Lock, AlertTriangle } from "lucide-react";
import FaqAccordion, { type FaqEntry } from "@/components/FaqAccordion";

const STEPS = [
  {
    icon: Upload,
    title: "1. Sözleşmenizi yükleyin",
    body: "PDF, DOCX, TXT veya Markdown (.md) formatında sözleşmenizi yükleyin. Birden fazla dosyayı aynı anda seçebilirsiniz.",
  },
  {
    icon: FileSearch,
    title: "2. Özeti çıkarılır",
    body: "Taraflar, tutar, başlangıç/bitiş tarihleri ve önemli yükümlülükler otomatik olarak bulunup sizin için kısa bir özet halinde sunulur.",
  },
  {
    icon: ShieldCheck,
    title: "3. Riskli maddeler işaretlenir",
    body: "Sözleşmeniz, sık karşılaşılan riskli ifadeler ve eksik olabilecek standart maddeler açısından taranır. Bulgular önem derecesine göre işaretlenir: kritik, yüksek, orta, düşük. Hangi konuların arandığı sözleşmenin türüne göre değişir — örneğin bir boşanma protokolünde ticari sözleşmelere özgü konular aranmaz.",
  },
  {
    icon: MessageSquareText,
    title: "4. Sorularınızı sorun",
    body: "Sözleşmeyle ilgili aklınıza takılan herhangi bir şeyi sohbet ekranına yazın. Verilen yanıt hangi maddeye dayandığını da gösterir, böylece kaynağını kendiniz de kontrol edebilirsiniz.",
  },
  {
    icon: GitCompareArrows,
    title: "5. Sözleşmeleri karşılaştırın",
    body: "Birden fazla sözleşmeyi seçip fesih, sorumluluk, ödeme gibi ortak konularda yan yana karşılaştırabilir, hangisinin sizin için daha koruyucu olduğunu görebilirsiniz.",
  },
];

const TODO = [
  "Sözleşmenizi yükleyin ve analizin tamamlanmasını bekleyin.",
  "Bulguları, özellikle \"Kritik\" ve \"Yüksek\" etiketli olanları dikkatle okuyun.",
  "Emin olmadığınız noktaları sohbet ekranında sorun — verilen kaynak maddeye tıklayıp orijinal metni kendiniz de kontrol edin.",
  "Önemli bir karar vermeden önce bulguları mutlaka bir avukatla teyit edin.",
];

const FAQ: FaqEntry[] = [
  {
    question: "Sözleşmelerim nereye yükleniyor, dışarı çıkıyor mu?",
    answer: "Hayır. Belgeleriniz yalnızca kendi bilgisayarınızda saklanır; internete veya başka bir yere gönderilmez.",
  },
  {
    question: "Risk puanı nasıl hesaplanıyor?",
    answer:
      "Sözleşmenizde bulunan riskli noktalar önem derecesine göre (kritik, yüksek, orta, düşük) değerlendirilip 0-100 arasında tek bir puana dönüştürülür. Tek bir ciddi sorun bile puanı hızla yükseltir. Hangi konuların değerlendirmeye alınacağı sözleşmenin türüne göre değişir; örneğin bir aile hukuku belgesinde ticari sözleşmelere özgü konular puana katılmaz.",
  },
  {
    question: "Sistem hata yapabilir mi?",
    answer:
      "Evet, nadiren de olsa yanlış ya da eksik bir değerlendirme yapabilir. Bu yüzden özellikle önemli bulguları, sözleşmenizin orijinal metniyle karşılaştırarak kontrol etmenizi öneririz.",
  },
  {
    question: "Hangi dosya türlerini yükleyebilirim?",
    answer: "PDF, DOCX, TXT ve Markdown (.md) dosyaları desteklenir; tek seferde birden fazla dosya yükleyebilirsiniz.",
  },
  {
    question: "Analiz sonucuna güvenip bir avukata danışmadan karar verebilir miyim?",
    answer:
      "Hayır, önerilmez. Bu araç sözleşmenizi incelerken size yardımcı olmak için tasarlanmıştır; bir avukatın vereceği hukuki görüşün yerini tutmaz. Bağlayıcı bir karar vermeden önce bulguları mutlaka bir avukatla teyit edin.",
  },
  {
    question: "Karşılaştırma özelliği nasıl çalışıyor?",
    answer:
      "2 ile 5 arasında sözleşme seçtiğinizde, ortak konular (fesih, sorumluluk, ödeme gibi) yan yana bir tabloda gösterilir. Böylece örneğin iki kira sözleşmesinden hangisinin sizin için daha koruyucu olduğunu hızlıca görebilirsiniz.",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="flex flex-1 justify-center">
      <main className="w-full max-w-2xl px-6 py-10 lg:max-w-3xl xl:max-w-4xl">
        <header className="mb-8">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold tracking-[0.14em] text-gold-hover uppercase">
            <Scale className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
            Nasıl Çalışır
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-balance text-ink">
            Sözleşme Analiz Asistanı nedir?
          </h1>
          <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-ink-2">
            Sözleşmenizi yükleyin; içeriğini özetleyelim, dikkat etmeniz gereken maddeleri
            işaretleyelim, aklınıza takılan soruları yanıtlayalım ve isterseniz birden fazla
            sözleşmeyi karşılaştıralım. Her şey kendi bilgisayarınızda kalır, hiçbir belge
            dışarı gönderilmez.
          </p>
        </header>

        <section className="mb-10">
          <h2 className="mb-4 text-xs font-semibold tracking-[0.14em] text-ink-3 uppercase">
            Nasıl kullanılır?
          </h2>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {STEPS.map((step) => (
              <div key={step.title} className="card flex items-start gap-4 p-5">
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                  style={{ backgroundColor: "var(--accent-soft)" }}
                >
                  <step.icon className="h-4 w-4 text-accent" strokeWidth={1.6} aria-hidden />
                </div>
                <div>
                  <p className="font-medium text-ink">{step.title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-ink-2">{step.body}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-10">
          <h2 className="mb-4 text-xs font-semibold tracking-[0.14em] text-ink-3 uppercase">
            Ne yapmanız gerekiyor?
          </h2>
          <div className="card p-5">
            <ol className="space-y-3">
              {TODO.map((item, i) => (
                <li key={i} className="flex gap-3 text-sm leading-relaxed text-ink-2">
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                    style={{ backgroundColor: "var(--secondary-soft)", color: "var(--secondary)" }}
                  >
                    {i + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mb-10 space-y-3">
          <h2 className="text-xs font-semibold tracking-[0.14em] text-ink-3 uppercase">
            Gizlilik ve önemli uyarı
          </h2>
          <div className="card flex items-start gap-3 p-5">
            <Lock className="mt-0.5 h-5 w-5 shrink-0 text-secondary" strokeWidth={1.6} aria-hidden />
            <p className="text-sm leading-relaxed text-ink-2">
              Tüm belgeleriniz, sonuçlarınız ve sohbet geçmişiniz yalnızca kendi
              bilgisayarınızda saklanır. Hiçbir sözleşme metni internete veya başka bir yere
              gönderilmez.
            </p>
          </div>
          <div
            className="card flex items-start gap-3 p-5"
            style={{ borderColor: "var(--status-warning)" }}
          >
            <AlertTriangle
              className="mt-0.5 h-5 w-5 shrink-0"
              style={{ color: "var(--status-warning)" }}
              strokeWidth={1.6}
              aria-hidden
            />
            <p className="text-sm leading-relaxed text-ink-2">
              <span className="font-medium text-ink">Önemli uyarı: </span>
              Bu sistem, sözleşme inceleme sürecini desteklemek amacıyla geliştirilmiştir.
              Oluşturulan analiz ve cevaplar profesyonel hukuki danışmanlık yerine geçmez.
            </p>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-xs font-semibold tracking-[0.14em] text-ink-3 uppercase">
            Sık sorulan sorular
          </h2>
          <FaqAccordion items={FAQ} />
        </section>
      </main>
    </div>
  );
}
