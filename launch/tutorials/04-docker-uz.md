# 04-dars — Docker Compose bilan joylashtirish (Uzbek)

**Mavzu:** ARGO'ni Docker Compose bilan o'zingiz joylashtirish
**Til:** O'zbekcha (lotin yozuvi)
**Maqsadli davomiylik:** ~5 daqiqa

---

### 1-sahna — Kirish (0:00–0:25)

ON SCREEN: ARGO logotipi, so'ng terminal.

NARRATION: "Ushbu turkumdagi yakuniy videoga xush kelibsiz. Biz ARGO'ni
o'rnatdik, u bilan suhbatlashdik va Telegram botini uladik. Endi uni
serverda ishlatadigan tarzda joylashtiramiz — Docker Compose yordamida."

### 2-sahna — Arxitektura (0:25–1:15)

ON SCREEN: oddiy sxema —
```
[ argo-brain ]  <-- Unix socket -->  [ argo-core ]  --> port 8000
   Python miyasi    umumiy hajm          Rust gateway
```

NARRATION: "ARGO'ning Docker sozlamasida ikkita xizmat bor. argo-brain
— bu Python miyasi, u agent siklini Unix soketi orqali bajaradi.
argo-core — bu Rust shlyuzi, u HTTP API'ni 8000-portda taqdim etadi va
miya bilan o'sha soket orqali bog'lanadi. Compose fayli ularni ikkita
umumiy hajm bilan bog'laydi: biri soket uchun, ikkinchisi doimiy
ma'lumotlar uchun."

### 3-sahna — Compose fayli bilan tanishish (1:15–2:15)

ON SCREEN: ochilgan `docker-compose.yml`, sekin aylantirish.

NARRATION: "ARGO repozitoriy ildizida tayyor docker-compose.yml bilan
keladi. E'tibor bering: ikkala xizmat ham bir xil ARGO_IPC_SOCKET
qiymatidan foydalanadi — bu ular bo'lishadigan soket yo'li. argo-data
hajmi SQLite ma'lumotlar bazangiz va ko'nikmalaringizni saqlaydi, shuning
uchun ma'lumotlaringiz qayta ishga tushirishlardan keyin ham saqlanadi.
argo-core'da esa slesh-api-slesh-health endpointiga murojaat qiluvchi
holat tekshiruvi bor."

### 4-sahna — Yig'ish va ishga tushirish (2:15–3:25)

ON SCREEN:
```
docker compose up -d --build
```

NARRATION: "Repozitoriy ildizidan docker compose up buyrug'ini bajaring.
Tire-d bayrog'i uni fonda ishga tushiradi, tire-tire-build esa birinchi
marta tasvirlarni yig'adi. Docker Python va Rust tasvirlarini yig'adi va
ikkita konteynerni ishga tushiradi."

ON SCREEN:
```
docker compose ps
```

NARRATION: "Holatni docker compose ps buyrug'i bilan tekshiring.
argo-core healthy holatini ko'rsatguncha kuting — bu holat tekshiruvi
muvaffaqiyatli o'tganini bildiradi."

### 5-sahna — API'ni tekshirish (3:25–4:15)

ON SCREEN:
```
curl http://localhost:8000/api/health
```

NARRATION: "Endi uni xost tomonidan tekshiring. health endpointiga
so'rov OK javobini qaytarishi kerak. Shlyuz shuningdek suhbatlar uchun
slesh-api-slesh-chat va Prometheus uchun slesh-metrics taqdim etadi.
ARGO nusxangiz endi to'liq qiymatli, o'zingiz joylashtirgan xizmat
sifatida ishlamoqda."

### 6-sahna — Loglar va boshqaruv (4:15–4:45)

ON SCREEN:
```
docker compose logs -f
docker compose down
```

NARRATION: "Har bir xizmat nima qilayotganini kuzatish uchun docker
compose logs, hammasini to'xtatish uchun esa docker compose down dan
foydalaning. Ma'lumotlaringiz nomlangan hajmda xavfsiz saqlanadi va
keyingi ishga tushirishga tayyor turadi."

### 7-sahna — Yakun va chaqiriq (4:45–5:05)

ON SCREEN: ARGO logotipi, GitHub manzili, "E'tiboringiz uchun rahmat"
yozuvi.

NARRATION: "Mana ARGO Docker Compose bilan, butunlay o'zingizning
infratuzilmangizda joylashtirildi. ARGO ochiq kodli va MIT litsenziyasi
ostida, u umumiy chiqarish sari alfa bosqichida, shuning uchun hozir
qo'shilish uchun eng yaxshi vaqt. Repozitoriyga yulduzcha qo'ying, issue
oching, agar siz Markaziy Osiyo tillaridan birini bilsangiz, tuzatishlar
ayniqsa olqishlanadi. Butun turkumni tomosha qilganingiz uchun rahmat."
