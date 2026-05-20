# 03-dars — Telegram botini ulash (Uzbek)

**Mavzu:** ARGO'ni Telegram botiga ulash
**Til:** O'zbekcha (lotin yozuvi)
**Maqsadli davomiylik:** ~4 daqiqa

---

### 1-sahna — Kirish (0:00–0:25)

ON SCREEN: ARGO logotipi, so'ng Telegram suhbat oynasi.

NARRATION: "Yana xush kelibsiz. Hozirgacha biz ARGO bilan terminaldan
suhbatlashdik. Bu videoda biz ARGO'ga Telegram boti beramiz, shunda
istalgan odam u bilan telefonidan suhbatlasha oladi."

### 2-sahna — BotFather orqali bot yaratish (0:25–1:25)

ON SCREEN: Telegram ilovasi, @BotFather bilan suhbat.

NARRATION: "Telegram botlari BotFather nomli bot tomonidan yaratiladi.
Telegram'ni oching, BotFather'ni qidiring va suhbat boshlang.
Slesh-newbot buyrug'ini yuboring."

ON SCREEN (BotFather'ga yoziladi):
```
/newbot
```

NARRATION: "BotFather botingiz uchun nom va foydalanuvchi nomini
so'raydi. Istalganini tanlang — foydalanuvchi nomi 'bot' bilan tugashi
kerak. Tugatganingizda BotFather sizga token beradi. Bu token — maxfiy
ma'lumot, unga parol kabi munosabatda bo'ling."

### 3-sahna — Tokenni o'rnatish (1:25–2:15)

ON SCREEN:
```
export TELEGRAM_BOT_TOKEN=123456:ABC-your-token-here
```

NARRATION: "ARGO bot tokenini TELEGRAM_BOT_TOKEN nomli muhit
o'zgaruvchisidan o'qiydi. Uni terminalingizda o'rnating, BotFather bergan
tokenni joylashtiring. Doimiy sozlash uchun tokenni har safar yozish
o'rniga muhit faylingizga joylang."

### 4-sahna — Telegram kanalini ishga tushirish (2:15–3:05)

ON SCREEN:
```
cd argo-brain
python3 -m argo_brain telegram
```

NARRATION: "Endi telegram quyi buyrug'i bilan ARGO'ning Telegram
kanalini ishga tushiring. ARGO Telegram'ga ulanadi va xabarlarni
tinglashni boshlaydi. Bu jarayonni ishlab turgan holda qoldiring — aynan
u botingizga xizmat qiladi."

### 5-sahna — Bot bilan suhbatlashish (3:05–3:40)

ON SCREEN: Telegram ilovasi, yangi botni ochish va xabar yuborish.

NARRATION: "Telegram'da botingizni oching va unga xabar yuboring. ARGO
uni qabul qiladi, CLI'da ko'rgan o'sha agent siklini bajaradi va suhbatda
javob beradi. Tilni aniqlash ichiga o'rnatilgani sababli, unga o'zbek
yoki rus tilida yozishingiz mumkin — u o'sha tilda javob beradi."

ON SCREEN (bot suhbatida yoziladi):
```
Salom! O'zingni tanishtir.
```

### 6-sahna — Yakun va chaqiriq (3:40–4:05)

ON SCREEN: ARGO logotipi, GitHub manzili, "Keyingisi: Docker Compose
bilan joylashtirish" yozuvi.

NARRATION: "Mana ARGO asosida ishlaydigan Telegram boti tayyor. Esda
tuting: tokeningizni maxfiy saqlang va uni hech qachon repozitoriyga
qo'shmang. ARGO ochiq kodli, MIT litsenziyasi ostida va umumiy chiqarish
sari alfa bosqichida. Oxirgi videoda ARGO'ni Docker Compose yordamida
to'g'ri joylashtiramiz. E'tiboringiz uchun rahmat."
