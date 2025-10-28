# QA Test Hazırlığı

Bu doküman, yeni broker giriş & portföy yönetimi özelliklerini canlıya almadan önce nasıl test edebileceğinizi özetler.

## 1. Ortam Hazırlığı

1. **Bağımlılıklar**  
   ```bash
   pip install -r backend/requirements.txt
   pip install email-validator pytest
   ```

2. **Çevre değişkenleri**  
   - QA Postgres bağlantısını `.env` veya shell üzerinden hazırla:  
     `DATABASE_URL=postgresql://kullanici:sifre@qa-host:5432/metra_qa`
   - Cloudinary anahtarları varsa `.env` içinde bırak; aksi halde görsel yükleme devre dışı kalır.

3. **Migration**  
   QA veritabanında yeni tabloları oluştur:
   ```bash
   psql "$DATABASE_URL" -f backend/migrations/20241028_add_users_and_properties.sql
   ```

## 2. Premium Hesap Koşulu

- Premium ilan yetkisi vereceğiniz danışmanı `agents` tablosunda `is_premium = true` olarak işaretleyin.
- API üzerinden deneme yaparken önce `/agents/` endpointine `is_premium: true` içeren kayıt gönderin; kayıtlı olmayan veya premium olmayan e-posta ile `/auth/register` çağrıları 403 döner.
- Premium yetkisi kaldırılan kullanıcılar `/auth/login` sırasında da engellenir, böylece premium sosyal alanlar sadece yetkili danışmanlar tarafından kullanılır.

## 3. Otomatik API Testi (Lokal)

Lokal doğrulama için SQLite kullanan Pytest senaryosu hazır:
```bash
pytest tests/test_api.py
```

Bu test; kayıt → giriş → ilan ekleme, listeleme, güncelleme, silme → çıkış zincirini uçtan uca koşar ve canlı veritabanını etkilemez.

## 4. QA API Doğrulama (Postgres)

1. Backend’i QA bağlantısıyla başlat:  
   `uvicorn backend.main:app --reload --port 8000`

2. Postman/Hoppscotch/curl ile sırayla:
   - `POST /auth/register` (JSON): broker kaydı
   - `POST /auth/login` (form-data): token al → `X-Session-Token` header
   - `POST /properties/` (JSON + header): ilan ekle
   - `GET /properties/` ve `GET /properties/?only_mine=true`: veri kontrolü
   - `PUT /properties/{id}` / `DELETE /properties/{id}`: yetkili güncelle/sil
   - `POST /auth/logout`: token’ın kapanmasını doğrula

3. Postgres’te kayıtları teyit et:  
   `SELECT * FROM users;`  
   `SELECT * FROM properties;`

## 5. Landing Önizlemesi

Statik demo veriyi kontrol etmek için:
```bash
python -m http.server 8080 --directory landing
# tarayıcı: http://localhost:8080/main.html
```

Gerçek ilanları göstermek istediğinizde, `/properties/` API çağrısını yapan bir fetch/Alpine bloğu ekleyebilirsiniz.

## 6. Test Sonrası

- QA ortamında eklediğiniz broker/ilanları silmeyi unutmayın.
- Migration dosyasını production’a taşımadan önce QA sonuçlarını kaydedin.
