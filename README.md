# ClutterKill

ClutterKill is a multi-agent desktop application for automated file organization using local AI. 

## 📁 Directory Architecture

The project follows a structured modular architecture:

- **`ui/`**: Contains the graphical user interface components built with `PyQt6`.
- **`core/`**: Houses the core application logic (file management, quarantine, undo mechanisms).
- **`ai/`**: Contains AI models, agents, and configuration for handling language models and extraction tasks.
- **`tests/`**: Includes all the unit and integration tests driven by `pytest`.
- **`scripts/`**: Utility scripts (e.g., generating mock data for testing).
- **`docs/`**: Documentation files (architecture, AI models reports, etc.).

*Note: The `ui/`, `core/`, `ai/`, and `tests/` directories are Python packages and contain `__init__.py` files.*

## 📦 Dependencies & Installation

The project's Python dependencies are listed in `requirements.txt`, which include:
- **PyQt6**: For the desktop graphical interface.
- **Langchain & Langchain-Community**: For building and orchestrating AI agents.
- **PyMuPDF, Pytesseract, Pillow, python-docx, fpdf**: For processing and analyzing various document and image formats.
- **Pydantic**: For data validation.
- **Pytest**: For testing the codebase.
- **Ruff**: For extremely fast Python linting and code formatting.

### How to Install:
To set up your environment, install the dependencies using `pip`:
```bash
pip install -r requirements.txt
```
*(If you use `uv`, you can also run `uv pip install -r requirements.txt`)*

## 🛠️ Code Formatting & Pre-Commit Hooks

To ensure consistent code quality and formatting, this project is configured to use **`pre-commit`** with **`ruff`**. This will automatically format your Python code every time you make a commit.

### How to Use:
1. Ensure `pre-commit` is installed globally:
   ```bash
   pip install pre-commit
   ```
2. Install the Git hook script within your local repository:
   ```bash
   pre-commit install
   ```

Once installed, `ruff` will automatically format your code on `git commit`. If changes are made by the formatter, the commit will abort—simply `git add` the updated files and run `git commit` again.
