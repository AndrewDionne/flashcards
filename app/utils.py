import os
import re
import json
import shutil
import requests
from pathlib import Path
from flask import jsonify, redirect, url_for
from gtts import gTTS
from jinja2 import Environment, FileSystemLoader

from .git_utils import commit_and_push_changes
from .practice import generate_practice_html
from .flashcards import generate_flashcard_html
from .reading import generate_reading_html
from .listening import generate_listening_html
from .test import generate_test_html

from .sets_utils import (
    SETS_DIR, sanitize_filename,
    get_all_sets, load_set_modes, load_sets_for_mode
)


# === Utility ===

def open_browser():
    """Open local dev server in a browser."""
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()

# === Homepage Export ===
def export_homepage_static():
    """Re-render homepage index.html for GitHub Pages."""
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("index.html")
    sets = get_all_sets()
    set_modes = load_set_modes()
    rendered = template.render(sets=sets, set_modes=set_modes)
    (Path("docs") / "index.html").write_text(rendered, encoding="utf-8")

# === Azure Speech ===
def get_azure_token():
    """Request a temporary Azure speech token."""
    AZURE_SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY")
    AZURE_REGION = os.environ.get("AZURE_REGION", "canadaeast")
    if not AZURE_SPEECH_KEY:
        return jsonify({"error": "AZURE_SPEECH_KEY missing"}), 500

    url = f"https://{AZURE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY, "Content-Length": "0"}
    try:
        res = requests.post(url, headers=headers)
        res.raise_for_status()
        return jsonify({"token": res.text, "region": AZURE_REGION})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

# === Set Creation / Deletion ===
def handle_flashcard_creation(form):
    """Create new set from form data and generate HTML/audio."""
    set_name = form.get("set_name", "").strip()
    json_input = form.get("json_input", "").strip()

    # Safety checks
    if not set_name:
        return "<h2 style='color:red;'>❌ Set name is required.</h2>", 400
    if (SETS_DIR / set_name).exists():
        return f"<h2 style='color:red;'>❌ Set '{set_name}' already exists.</h2>", 400

    # Parse JSON
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError:
        return "<h2 style='color:red;'>❌ Invalid JSON input format.</h2>", 400

    # Validate entries
    for entry in data:
        if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
            return "<h2 style='color:red;'>❌ Each entry must have 'phrase', 'pronunciation', and 'meaning'.</h2>", 400

    # Prepare folders
    audio_dir = Path("docs/static") / set_name / "audio"
    output_dir = Path("docs/output") / set_name
    set_dir = SETS_DIR / set_name
    for path in (audio_dir, output_dir, set_dir):
        path.mkdir(parents=True, exist_ok=True)

    # Generate audio
    for i, entry in enumerate(data):
        phrase = entry["phrase"]
        filename = f"{i}_{sanitize_filename(phrase)}.mp3"
        filepath = audio_dir / filename
        if not filepath.exists():
            gTTS(text=phrase, lang="pl").save(filepath)

    # Save JSON data
    with open(set_dir / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Generate HTML for all modes
    generate_flashcard_html(set_name, data)
    generate_practice_html(set_name, data)
    generate_test_html(set_name, data)
    generate_reading_html(set_name, data)
    generate_listening_html(set_name, data)

    commit_and_push_changes(f"✅ Add new set: {set_name}")
    return redirect(url_for("manage_sets"))

def delete_set(set_name: str):
    """Delete set folders from all locations."""
    for path in [
        Path("docs/output") / set_name,
        Path("docs/static") / set_name,
        SETS_DIR / set_name
    ]:
        if path.exists():
            shutil.rmtree(path)
            print(f"🧹 Deleted folder: {path}")
        else:
            print(f"⚠️ Folder not found: {path}")

    commit_and_push_changes(f"🗑️ Deleted set: {set_name}")
    print(f"✅ Deleted set: {set_name}")

def delete_set_and_push(set_name: str):
    delete_set(set_name)
