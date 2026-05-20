# 01-dars — ARGO'ni 5 daqiqada o'rnatish (Uzbek)

**Mavzu:** O'rnatish
**Til:** O'zbekcha (lotin yozuvi)
**Maqsadli davomiylik:** ~4 daqiqa

---

### 1-sahna — Kirish (0:00–0:25)

ON SCREEN: ARGO logotipi, so'ng toza terminal oynasi.

NARRATION: "Assalomu alaykum va ARGO'ga xush kelibsiz. ARGO — bu ochiq
kodli, o'zingiz joylashtiradigan sun'iy intellekt agenti platformasi.
Keyingi bir necha daqiqada uni noldan o'rnatamiz. Yaxshi xabar: o'rnatish
uchun deyarli hech narsa kerak emas — ARGO miyasi faqat Python standart
kutubxonasida ishlaydi."

### 2-sahna — Nima kerak (0:25–0:55)

ON SCREEN:
```
python3 --version
git --version
```

NARRATION: "Sizga ikki narsa kerak: Python 3 va Git. ARGO'ni sinab
ko'rish uchun shuning o'zi yetarli. Keyinroq Rust shlyuzini yig'moqchi
bo'lsangiz, Rust vositalari ham kerak bo'ladi, ammo bu videoda ulardan
foydalanmaymiz."

### 3-sahna — Repozitoriyni klonlash (0:55–1:35)

ON SCREEN:
```
git clone https://github.com/argo-agent/argo.git
cd argo
```

NARRATION: "Avval repozitoriyni klonlang va uning papkasiga kiring. ARGO
ikki qismdan iborat: argo-core — Rust shlyuzi va argo-brain — Python
miyasi. Hozir biz miya bilan ishlaymiz."

### 4-sahna — O'rnatish skriptini ishga tushirish (1:35–2:40)

ON SCREEN:
```
./scripts/setup.sh
```

NARRATION: "ARGO bir qadamda hammasini bajaradigan o'rnatish skriptiga
ega. U vositalarni tekshiradi, Rust mavjud bo'lsa argo-core'ni yig'adi va
maqbul standart sozlamalarni o'rnatadi. Hammasini qo'lda qilishni afzal
ko'rsangiz, interaktiv sozlash ustasini ishga tushiring."

ON SCREEN:
```
cd argo-brain
python3 -m argo_brain setup
```

NARRATION: "Sozlash ustasi sizni asosiy konfiguratsiya bo'yicha qadamma-
qadam yo'naltiradi."

### 5-sahna — doctor buyrug'i bilan tekshirish (2:40–3:25)

ON SCREEN:
```
python3 -m argo_brain doctor
```

NARRATION: "Endi doctor buyrug'ini bajaring. Bu ARGO'ning ichki
diagnostikasi — u o'rnatishingizni tekshiradi va xato ko'ringan har
narsa haqida xabar beradi. Agar barcha qatorlar yashil bo'lsa, siz
tayyorsiz."

### 6-sahna — Birinchi ishga tushirish (3:25–3:50)

ON SCREEN:
```
python3 -m argo_brain chat
```

NARRATION: "Ishlayotganiga ishonch hosil qilish uchun chatni ishga
tushiring. U mahalliy sinov modelidan foydalanadi, shuning uchun unga na
API kalit, na internet kerak. Xabar yozing — va ARGO javob beradi."

### 7-sahna — Yakun va chaqiriq (3:50–4:10)

ON SCREEN: ARGO logotipi, GitHub manzili va "Keyingisi: birinchi
suhbatingiz" yozuvi.

NARRATION: "Mana shu — ARGO o'rnatildi. ARGO ochiq kodli va MIT
litsenziyasi ostida tarqatiladi, hozir esa umumiy chiqarish sari alfa
bosqichida, shuning uchun fikr-mulohazangiz haqiqatan ham yordam beradi.
Bizni GitHub'da yulduzcha bilan belgilang va birinchi haqiqiy suhbat
hamda CLI bilan tanishadigan keyingi videoni tomosha qiling. E'tiboringiz
uchun rahmat."
