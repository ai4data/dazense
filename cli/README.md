# nao CLI

Command-line interface for nao chat.

## Installation

```bash
pip install nao-core
```

## Usage

### Start the chat interface

```bash
nao chat
```

This will start the nao chat server and open the web interface in your browser at `http://localhost:5005`.

## Development

### Building the package

```bash
cd cli
python build.py
```

This will:
1. Build the frontend with Vite
2. Compile the backend with Bun into a standalone binary
3. Bundle everything into a Python wheel in `dist/`

Options:
- `--force` / `-f`: Force rebuild the server binary
- `--skip-server`: Skip server build, only build Python package

### Installing for development

```bash
cd cli
pip install -e .
```

### Publishing to PyPI

```bash
# Build first
python build.py

# Publish
uv publish dist/*
```

## Architecture

```
nao chat (CLI command)
    ↓ spawns
nao-chat-server (Bun-compiled binary)
    ↓ serves
Backend API + Frontend Static Files
    ↓
Browser at http://localhost:5005
```
