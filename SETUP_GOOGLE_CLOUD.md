# Huong Dan Setup Google Cloud

---

## Ai can doc tai lieu nay?

| Doi tuong | Can lam gi? |
|-----------|-------------|
| **Developer / Chu app** | Doc toan bo tai lieu nay - setup 1 lan duy nhat |
| **Nguoi dung cuoi (End user)** | Chi can dang nhap Google trong app - khong can setup gi |

> **Nguoi dung cuoi KHONG can tao Google Cloud, KHONG can file `client_secrets.json`.**  
> File do da duoc developer tao san va dong goi vao trong app roi.

---

## PHAN 1 — Danh cho Developer (Chi can lam 1 LAN duy nhat)

> **Thoi gian:** ~10 phut  
> **Yeu cau:** Tai khoan Google (Gmail / Google Workspace)

Buoc nay ban (developer) thuc hien de tao ra file `client_secrets.json` roi ban giao cho tat ca nguoi dung.
Nguoi dung chi can chay app va dang nhap, KHONG can biet den Google Cloud.

```
Buoc 1  Tao Google Cloud Project
Buoc 2  Bat 2 API (Drive + Sheets)
Buoc 3  Cau hinh man hinh dang nhap (OAuth Consent Screen)
Buoc 4  Tao file client_secrets.json
Buoc 5  Dat file vao thu muc goc cua app truoc khi phat hanh
```

---

### Buoc 1 - Tao Google Cloud Project

1. Mo trinh duyet, truy cap: **https://console.cloud.google.com**
2. Dang nhap bang tai khoan Google cua ban
3. Goc tren trai, click ten project hien tai hoac **"Select a project"**
4. Click **"NEW PROJECT"** (goc tren phai cua popup)
5. Dien thong tin:
   - **Project name:** `Thumb Pipeline` (hoac ten ban muon)
   - **Organization:** de mac dinh
6. Click **"CREATE"** -> Doi khoang 10 giay
7. Chon project vua tao tu danh sach

---

### Buoc 2 - Bat Google Drive API va Sheets API

Ban can bat **2 API** nay. Lam lan luot tung cai:

#### Bat Google Drive API

1. Trong thanh tim kiem o tren cung, go: **`Google Drive API`**
2. Click ket qua **"Google Drive API"**
3. Click nut **"ENABLE"** (mau xanh)
4. Doi den khi trang chuyen sang "Enabled"

#### Bat Google Sheets API

1. Quay lai trang chu Console (click logo Google Cloud goc tren trai)
2. Trong thanh tim kiem, go: **`Google Sheets API`**
3. Click ket qua **"Google Sheets API"**
4. Click nut **"ENABLE"**

---

### Buoc 3 - Cau Hinh OAuth Consent Screen

Day la man hinh hien ra khi nguoi dung dang nhap vao app.
Buoc nay **bat buoc** phai lam truoc khi tao credentials.

1. Menu trai: **"APIs & Services"** -> **"OAuth consent screen"**
2. Chon **"External"** -> Click **"CREATE"**
3. Dien form **"App information"**:

   | Truong | Gia tri |
   |--------|---------|
   | App name | `Thumb Pipeline` |
   | User support email | chon email cua ban tu dropdown |
   | Developer contact email | nhap email cua ban |

   > Cac truong khac de trong, khong can dien

4. Click **"SAVE AND CONTINUE"** qua 4 trang

   > **Trang "Test users"** (Developer tu lam, nguoi dung KHONG can lam gi):
   > - Neu app o che do **Testing**: Developer them email tung nguoi dung vao day thi ho moi dang nhap duoc.
   > - Neu app da o che do **In production**: Bo qua, khong can them ai - bat ky tai khoan Google nao cung dang nhap duoc.
   >
   > **App hien tai da "In production" -> Khong can lam buoc nay.**

5. Trang cuoi (Summary): click **"BACK TO DASHBOARD"**

---

### Buoc 4 - Tao OAuth2 Credentials (File client_secrets.json)

Day la buoc quan trong nhat - tao ra "chia khoa" de app ket noi Google.

1. Menu trai: **"APIs & Services"** -> **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"**
3. Chon **"OAuth client ID"**
4. **Application type**: chon **`Desktop app`**
5. **Name:** de mac dinh hoac dat ten `Thumb Pipeline Desktop`
6. Click **"CREATE"**
7. Popup hien ra -> Click **"DOWNLOAD JSON"**
8. File tai ve ten dang `client_secret_xxx.json`

   **Doi ten file thanh:** `client_secrets.json`

9. **Chep file vao thu muc goc cua app:**
   ```
   Colab/
   +-- client_secrets.json   <- dat vao day
   +-- backend/
   +-- frontend/
   ```

---

### Buoc 4b (Tuy chon) - Chuyen sang "In Production"

Mac dinh app o che do **Testing** - chi nhung email ban them vao "Test users" moi dang nhap duoc.

Neu muon **bat ky tai khoan Google nao cung co the dang nhap** ma khong can them thu cong:

1. Vao **"OAuth consent screen"**
2. Click **"PUBLISH APP"** -> Xac nhan

> **Luu y:** Nguoi dung se thay man hinh canh bao "unverified app" cua Google.
> Day la binh thuong vi app chua gui Google xet duyet (chi can cho noi bo).
> Nguoi dung bam **"Advanced" -> "Go to Thumb Pipeline (unsafe)"** la tiep tuc duoc.

---

### Buoc 5 - Dat file truoc khi phat hanh

Sau khi co `client_secrets.json`, dat vao thu muc goc cua project:

```
Colab/
+-- client_secrets.json   <- FILE NAY PHAI CO TRUOC KHI BUILD/CHAY APP
+-- backend/
+-- frontend/
+-- src-tauri/
```

File nay duoc dong goi cung voi app. **Nguoi dung cuoi khong can lam buoc nay.**

---

## PHAN 2 — Danh cho Nguoi Dung Cuoi (End User)

> **Nguoi dung cuoi khong can setup Google Cloud hay tao file gi ca.**  
> Developer da chuan bi san roi. Ban chi can dang nhap.

### Dang nhap lan dau trong app

> Chi can lam **mot lan duy nhat**. Sau do app tu nho tai khoan.

1. Mo app **Thumb Pipeline**
2. Nhin vao phan **"Tai khoan Google"**
3. Click nut **"Dang nhap"**
4. Trinh duyet tu dong mo -> Chon tai khoan Google cua ban -> Click **"Allow"**

   > Neu thay canh bao **"This app isn't verified"**: click **"Advanced"** -> **"Go to Thumb Pipeline (unsafe)"** -> Tiep tuc.
   > Day la hoan toan an toan - app do chinh cong ty ban cung cap.

5. Quay lai app -> Badge xanh la = Thanh cong!

---

## Xu Ly Loi Thuong Gap

### Loi: "This app isn't verified"

> Google hien canh bao vi app chua duoc Google xet duyet chinh thuc.

**Cach xu ly:** Click **"Advanced"** -> **"Go to Thumb Pipeline (unsafe)"** -> Tiep tuc dang nhap.
Day la hoan toan an toan vi day la app noi bo.

---

### Loi: "Access blocked: Authorization Error" (Error 403)

**Nguyen nhan:** App dang o che do **Testing** va email ban dang nhap chua duoc developer them vao danh sach.

**Nguoi dung:** Lien he developer de duoc them email vao.

**Developer - Cach xu ly:**
1. Vao Google Cloud Console -> **"OAuth consent screen"**
2. Keo xuong phan **"Test users"**
3. Click **"+ ADD USERS"**
4. Nhap email cua nguoi dung -> **"SAVE"**
5. Hoac: Chuyen app sang **"In production"** (xem Buoc 4b) de khoi can them thu cong

---

### Loi: "Khong tim thay client_secrets.json"

**Danh cho developer - Cach xu ly:**
- Ten file chinh xac la `client_secrets.json` (khong phai `client_secret_abc123.json`)
- File nam trong thu muc goc `Colab/`, **khong phai** trong `backend/`

---

### Loi: "redirect_uri_mismatch"

**Nguyen nhan:** Application type khong phai Desktop app.

**Cach xu ly:**
1. Vao **"Credentials"** -> Click vao OAuth client ID vua tao
2. Kiem tra **"Application type"** co phai **"Desktop app"** khong
3. Neu khong -> Xoa credential -> Tao lai voi type **"Desktop app"**

---

## FAQ

**Q: Nguoi dung co can tao Google Cloud Project khong?**
> **Khong.** Developer tao 1 lan duy nhat. Nguoi dung chi can dang nhap bang tai khoan Google cua ho.

**Q: `client_secrets.json` la gi, co the chia se khong?**
> File nay la thong tin dinh danh cua APP (khong phai tai khoan ca nhan).
> Developer dat vao app, nguoi dung khong can biet den file nay.
> Co the chia se file nay cho dong nghiep neu ho cung deploy app.

**Q: `token.json` la gi?**
> `token.json` la token dang nhap ca nhan, duoc tao tu dong sau khi nguoi dung dang nhap.
> **Khong chia se file nay** vi no chua thong tin dang nhap ca nhan.

**Q: Token het han co can dang nhap lai khong?**
> Khong. App tu dong refresh token ngam.
> Chi can dang nhap lai khi ban chu dong xoa `token.json` hoac thu hoi quyen trong Google Account.

**Q: Muon doi sang tai khoan khac?**
> Click **"Xoa token"** trong app -> Xac nhan -> Click **"Dang nhap"** -> Dang nhap tai khoan moi.

**Q: Co bao nhieu nguoi co the dang nhap?**
> Neu app o che do **Testing**: toi da 100 tai khoan (phai them thu cong).
> Neu app o che do **In production**: khong gioi han, bat ky tai khoan Google nao cung dang nhap duoc.

---

## Checklist Nhanh

### Developer (Chi lam 1 lan)
```
[ ] Da tao Google Cloud Project
[ ] Da bat Google Drive API
[ ] Da bat Google Sheets API
[ ] Da cau hinh OAuth consent screen (App name + email)
[ ] Da tao OAuth Client ID voi type Desktop app
[ ] Da tai file JSON va doi ten thanh client_secrets.json
[ ] Da dat client_secrets.json vao thu muc goc Colab/
[ ] (Tuy chon) Da chuyen sang In Production neu muon mo rong nguoi dung
```

### Nguoi dung cuoi (Chi lam 1 lan)
```
[ ] Mo app Thumb Pipeline
[ ] Click "Dang nhap" -> Chon tai khoan Google -> Allow
[ ] Badge xanh hien thi = Hoan tat
```