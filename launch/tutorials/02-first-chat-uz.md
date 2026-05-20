# 02-dars — Birinchi suhbat va CLI bilan ishlash (Uzbek)

**Mavzu:** Birinchi suhbat va buyruqlar qatori interfeysi
**Til:** O'zbekcha (lotin yozuvi)
**Maqsadli davomiylik:** ~5 daqiqa

---

### 1-sahna — Kirish (0:00–0:25)

ON SCREEN: ARGO logotipi, so'ng terminal.

NARRATION: "Yana xush kelibsiz. O'tgan videoda biz ARGO'ni o'rnatdik.
Endi undan amalda foydalanamiz — birinchi suhbatimizni o'tkazamiz,
buyruqlar qatori interfeysini ko'rib chiqamiz va ARGO tillarni qanday
aniqlashini ko'ramiz."

### 2-sahna — CLI bilan umumiy tanishuv (0:25–1:05)

ON SCREEN:
```
python3 -m argo_brain --help
```

ON SCREEN (sanab o'tilgan buyruqlarni ajratib ko'rsatish):
```
setup     doctor    chat      tui
serve     ipc       telegram  mcp
selftest  version
```

NARRATION: "ARGO bitta kirish nuqtasiga ega — argo_brain moduli — va
bir nechta quyi buyruqlarga. setup va doctor buyruqlaridan biz allaqachon
foydalandik. Bugun asosiysi — chat. Shuningdek, HTTP shlyuz uchun serve,
Telegram bot uchun telegram va kengaytirilgan terminal interfeysi uchun
tui mavjud."

### 3-sahna — Chatni ishga tushirish (1:05–1:45)

ON SCREEN:
```
python3 -m argo_brain chat
```

NARRATION: "chat buyrug'ini bajaring. U interaktiv seansni ochadi.
Standart holatda mahalliy sinov modelidan foydalaniladi, shuning uchun
API kalit kerak emas — bu agent qanday ishlashini o'rganish uchun juda
qulay. Keling, salomlashamiz."

ON SCREEN (foydalanuvchi yozadi):
```
> Hello, what can you do?
```

NARRATION: "ARGO javob beradi va siz suhbatni davom ettira olasiz."

### 4-sahna — Ko'p tilli suhbat (1:45–2:55)

ON SCREEN (foydalanuvchi yozadi):
```
> Salom! Bugun ob-havo qanday?
```

NARRATION: "Mana ARGO aynan shu uchun yaratilgan qism. Men buni o'zbek
tilida yozdim. ARGO tilni aniqlaydi va javobni o'sha tilda qaytaradi.
Keling, rus tilini ham sinab ko'ramiz."

ON SCREEN (foydalanuvchi yozadi):
```
> Привет! Расскажи о себе.
```

NARRATION: "Rus tili ham xuddi shunday ishlaydi. ARGO o'zbek, rus,
qozoq, qirg'iz, tojik va ingliz tillarini qo'llab-quvvatlaydi — tilni
aniqlash yon tomondan qo'shilgan emas, balki ichiga o'rnatilgan."

### 5-sahna — Agent sikli va vositalar (2:55–4:00)

ON SCREEN (foydalanuvchi yozadi):
```
> What files are in the current directory?
```

NARRATION: "ARGO shunchaki chat-bot emas — u agent. So'rov uchun amal
kerak bo'lsa, ARGO rejalashtiradi, so'ng vositani bajaradi, keyin
natijadan foydalanadi. Bu 'rejalashtir, so'ng bajar' sikli. Bugun ARGO
13 ta o'rnatilgan vosita bilan keladi, jumladan buyruq qatori, fayllar,
Git va Docker."

ON SCREEN: agent vosita qadamini, so'ng javobni ko'rsatadi.

NARRATION: "Bu yerda vosita qadami, so'ng natija asosida tuzilgan
yakuniy javobni ko'rishingiz mumkin."

### 6-sahna — Xotira (4:00–4:35)

ON SCREEN (foydalanuvchi yozadi):
```
> My name is Aziz.
> What is my name?
```

NARRATION: "ARGO suhbat doirasidagi kontekstni eslab qoladi. U qisqa
muddatli xotirani jarayon ichida, uzoq muddatli saqlashni esa o'z
diskingizdagi mahalliy SQLite ma'lumotlar bazasida saqlaydi — tarixingiz
hech qachon kompyuteringizdan chiqmaydi."

### 7-sahna — Yakun va chaqiriq (4:35–5:00)

ON SCREEN: ARGO logotipi, GitHub manzili, "Keyingisi: Telegram botini
ulash" yozuvi.

NARRATION: "Mana ARGO bilan birinchi suhbatingiz: CLI, ko'p tilli
javoblar, vositalar va xotira. ARGO ochiq kodli va MIT litsenziyasi
ostida, hozir umumiy chiqarish sari alfa bosqichida — uni sinab ko'ring
va nima buzilganini bizga ayting. Keyingi videoda ARGO'ni Telegram botiga
ulaymiz. E'tiboringiz uchun rahmat."
