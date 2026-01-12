# AsyncSqliteManager Documentation

This directory contains the Sphinx documentation for AsyncSqliteManager.

## Building the Documentation

### Requirements

```bash
pip install sphinx sphinx-rtd-theme
```

### Build HTML Documentation

```bash
cd docs
make html
```

Or using sphinx-build directly:

```bash
sphinx-build -b html . _build/html
```

The generated HTML documentation will be in `_build/html/`. Open `_build/html/index.html` in your browser to view it.

### Other Formats

Build PDF (requires LaTeX):
```bash
make latexpdf
```

Build EPUB:
```bash
make epub
```

## Documentation Structure

- `index.rst` - Main documentation index
- `quickstart.rst` - Quick start guide
- `features.rst` - Detailed feature documentation
- `examples.rst` - Practical examples
- `changelog.rst` - Version history and changes
- `api/` - API reference documentation
  - `manager.rst` - Manager class documentation
  - `transaction.rst` - Transaction class documentation
  - `row_factory.rst` - Type conversion functions
  - `exceptions.rst` - Exception classes

## Viewing the Documentation

After building, you can view the documentation by opening `_build/html/index.html` in your web browser.

For local development, you can use Python's built-in HTTP server:

```bash
cd _build/html
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.
