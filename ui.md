# GÖREV: Flutter Medikal Asistan UI/UX Geliştirme

Benim için "Türkçe Akıllı Tıbbi Asistan" (Smart Medical Assistant) projesinin Flutter frontend arayüzlerini (UI) kodlamanı istiyorum. 

## 🎨 Tasarım Sistemi ve Renk Paleti
Uygulamanın profesyonel, temiz ve güven veren bir "sağlık/medikal" teması olmalı. Lütfen şu renkleri ana tema olarak kullan:
* **Primary Color:** Turkuaz/Medikal Yeşili (Örn: `Color(0xFF00A676)` veya `Colors.teal`)
* **Background Color:** Çok açık, temiz bir gri (Örn: `Color(0xFFF5F7FA)`)
* **Surface/Card Color:** Saf Beyaz (`Color(0xFFFFFFFF)`)
* **Text Colors:** Koyu Lacivert/Siyah tonları (Örn: `Color(0xFF2D3142)`) ve alt metinler için gri.

Lütfen `lib/presentation/screens/` dizini altında şu 4 ekranı, modern ve estetik Widget'lar (Card, ListTile, FloatingActionButton, SafeArea vs.) kullanarak tasarla. Şimdilik state management (BLoC/Riverpod) bağlama, sadece UI tasarımlarını (Stateless/Stateful) ve dummy (örnek) verilerle doldurulmuş hallerini ver.

### 1. `input_screen.dart` (Profil ve Karşılama)
* Kullanıcının ad, yaş, boy, kilo ve temel sağlık/fitness hedeflerini girdiği şık bir form ekranı.
* Form elemanları modern, yuvarlak hatlı (rounded corners) TextFormField'lardan oluşsun.
* Altta geniş, yeşil bir "Kaydet ve Başla" butonu olsun.

### 2. `home_screen.dart` (Ana Gösterge Paneli)
* Üstte bir selamlama ("Merhaba Şenol, bugün nasılsın?").
* Ortada yaklaşan hastane randevularını gösteren şık bir Card widget (Tarih, Hastane, Doktor Branşı).
* Sağ alt köşede asistanla konuşmayı başlatacak belirgin, yeşil bir FloatingActionButton (üzerinde bir robot veya chat ikonu).

### 3. `chat_screen.dart` (Akıllı Asistan Sohbeti)
* WhatsApp tarzı bir mesajlaşma arayüzü. 
* Kullanıcı mesajları sağda (yeşil baloncuk, beyaz yazı), asistan mesajları solda (beyaz baloncuk, koyu gri yazı) olsun.
* Mesaj yazma alanının hemen üstünde "Randevu Al", "Baş Ağrım Var", "Tahlil Sonucum" gibi yatay kaydırılabilir (horizontal scroll) hızlı aksiyon (quick reply) çipleri (ActionChip) bulunsun.

### 4. `result_screen.dart` (Randevu / Analiz Sonucu)
* Randevu başarıyla oluşturulduğunda veya asistan uzun bir tıbbi tavsiye verdiğinde açılan özet ekranı.
* Üstte büyük bir yeşil onay işareti (Check icon).
* Altında randevu detaylarını veya tıbbi tavsiye özetini gösteren geniş, gölgeli (box shadow) temiz bir kart tasarımı.
* En altta "Ana Ekrana Dön" butonu.

Lütfen ekranlar arası geçişleri şimdilik `Navigator.push` kullanarak birbirine bağla ki arayüzü çalıştırıp test edebileyim.