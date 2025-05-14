# 🧱 Django Package Template

A modern, minimal, and production-ready template for building and publishing reusable Django packages to PyPI with ease.

🔗 GitHub: [ganiyevuz/django-package-template](https://github.com/ganiyevuz/django-package-template)

---

## ✨ Features

- ✅ Clean and minimal project structure for Django package development
- ⚙️ CI/CD via GitHub Actions for testing and automated PyPI publishing
- 📦 Modern dependency management with [`uv`](https://github.com/astral-sh/uv)
- 🐍 Python 3.10–3.13 & Django 4.2–5.2 support
- 🧪 Preconfigured pytest and coverage
- 🧹 Makefile with common development commands
- 📄 MIT License

---

## 🚀 Quickstart

### 1. Create a New Package from Template

```bash
# Clone the template repository
git clone https://github.com/ganiyevuz/django-package-template.git your-package-name
cd your-package-name

# Reinitialize git
rm -rf .git
git init
git add .
git commit -m "Initial commit using Django package template"
````

---

### 2. Customize Metadata

Edit the following files:

* `pyproject.toml` – package name, version, author, dependencies
* `README.md` – your own documentation
* `LICENSE` – update copyright

You can also rename the main Django app inside `src/` to match your desired package name.

---

### 3. Set Up the Development Environment

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies with dev tools
uv pip install -e ".[dev]"
```

---

### 4. Start Coding 🧑‍💻

Implement your Django package inside the `src/your_package_name/` directory.

```text
src/
└── your_package_name/
    ├── __init__.py
    ├── apps.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── templates/
    └── static/
```

---

### 5. Use the Makefile 🛠️

```bash
make install     # Install the package with dev dependencies
make test        # Run tests with pytest
make lint        # Lint with flake8, isort, black
make coverage    # Run tests with coverage
make dist        # Build a distributable package
make clean       # Clean build artifacts
```

---

## ✅ GitHub Actions: CI/CD

This template comes with GitHub Actions for:

* Running tests and linting on pushes and PRs
* Publishing to PyPI on version tag push (e.g., `v0.1.0`)

### 🔐 PyPI Configuration

1. Go to your GitHub repo → Settings → Secrets → Actions
2. Add:

    * `PYPI_USERNAME`
    * `PYPI_PASSWORD`

### 🚢 Release

```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

---

## 🧪 Project Structure

```text
django-package-template/
├── .github/workflows/    # GitHub Actions
├── src/your_package/     # Your Django app/package
├── tests/                # Unit tests
├── pyproject.toml        # Project metadata and dependencies
├── Makefile              # Common development tasks
├── LICENSE               # MIT License
├── README.md             # This file
└── .gitignore
```

---

## 🤝 Contributing

Got improvements?

```bash
git checkout -b feature/my-feature
git commit -m "Add my feature"
git push origin feature/my-feature
```

Then open a Pull Request 🧷

---

## 📄 License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.

