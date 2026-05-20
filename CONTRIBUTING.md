# Hissa qo'shish — ARGO Agent

ARGO ochiq manbali loyiha. PR'lar va issue'lar kutiladi.

## Ishni boshlash

```bash
git clone https://github.com/oybek1097/ARGO.git
cd ARGO
./scripts/setup.sh
```

## argo-brain (Python)

```bash
cd argo-brain
python3 -m unittest discover -s tests   # testlar (73 ta, yashil bo'lishi shart)
python3 -m argo_brain selftest          # smoke test
```

- Python 3.11+ talab qilinadi.
- Yadro **faqat stdlib** bilan ishlaydi — yangi bog'liqlik qo'shishdan oldin
  muhokama qiling.
- **Kod kommentariyalari ingliz tilida** yoziladi (jahon tili — global
  hissadorlar uchun).

## argo-core (Rust)

```bash
cd argo-core
cargo test
cargo build --release
cargo clippy -- -D warnings
cargo fmt --check
```

## PR jarayoni (TZ 11-bo'lim)

1. Issue ochib muhokama qiling.
2. Branch yarating, o'zgartiring, testlarni yashil saqlang.
3. PR yuboring — CI yashil bo'lishi shart.
4. Commit xabarlarida `Signed-off-by:` trailer bo'lsin.

## Kod uslubi

| Til | Lint | Format |
|---|---|---|
| Python | `ruff` | `ruff format` |
| Rust | `cargo clippy` | `cargo fmt` |

## Litsenziya

Hissa qo'shish orqali kodingiz MIT litsenziyasi ostida tarqatilishiga rozilik
bildirasiz.
