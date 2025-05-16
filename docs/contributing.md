# 🤝 Contributing

## 👣 Steps to Contribute

1. Fork and branch:

```bash
git checkout -b feature/my-change
````

2. Format and lint:

```bash
make lint
```

3. Test:

```bash
pytest
```

4. Open a Pull Request!

---

## 🧪 Local Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

