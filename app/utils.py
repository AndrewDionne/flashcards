import os, re, json, shutil
from flask import jsonify, redirect, render_template
from gtts import gTTS
import requests
from pathlib import Path
from .git_utils import commit_and_push_changes
from .practice import generate_practice_html
from .flashcards import generate_flashcard_html
from .reading import generate_reading_html
from .listening import generate_listening_html
from .test import generate_test_html
from flask import render_template
from jinja2 import Environment, FileSystemLoader
SETS_DIR = Path("docs/sets")

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9]', '_', text)

def open_browser():
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()

def export_homepage_static():
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("index.html")
    
    sets = get_all_sets()
    set_modes = load_set_modes()
    
    rendered = template.render(sets=sets, set_modes=set_modes)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(rendered)

def load_sets_with_counts():
    sets_root = Path("docs/output")
    static_root = Path("docs/static")
    sets = []

    for output_set in sorted(sets_root.iterdir()) if sets_root.exists() else []:
        if output_set.is_dir():
            audio_path = static_root / output_set.name / "audio"
            count = len(list(audio_path.glob("*.mp3"))) if audio_path.exists() else 0
            sets.append({"name": output_set.name, "count": count})

    return sets

def load_sets_for_mode(mode):
    sets = load_sets_with_counts()
    set_modes = load_set_modes()
    return [s for s in sets if mode in set_modes.get(s["name"], [])]

def get_azure_token():
    AZURE_SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY")
    AZURE_REGION = os.environ.get("AZURE_REGION", "canadaeast")

    if not AZURE_SPEECH_KEY:
        return jsonify({"error": "AZURE_SPEECH_KEY missing"}), 500

    url = f"https://{AZURE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY, "Content-Length": "0"}

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return jsonify({"token": response.text, "region": AZURE_REGION})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

def get_all_sets():
    sets_root = SETS_DIR
    return sorted([s.name for s in SETS_DIR.iterdir() if s.is_dir()])


def load_set_modes():
    config_path = SETS_DIR / "mode_config.json"
    return json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

def save_set_modes(data):
    config_path = SETS_DIR / "mode_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def delete_set(set_name):
    from .git_utils import commit_and_push_changes

    output_dir = Path("docs/output") / set_name
    static_dir = Path("docs/static") / set_name
    sets_dir = SETS_DIR / set_name

    for path in [output_dir, static_dir, sets_dir]:
        if path.exists():
            shutil.rmtree(path)
            print(f"🧹 Deleted folder: {path}")
        else:
            print(f"⚠️ Folder not found: {path}")

    update_docs_homepage()
    commit_and_push_changes(f"🗑️ Deleted set: {set_name}")
    print(f"✅ Deleted set: {set_name}")

def delete_set_and_push(set_name):
    delete_set(set_name)
    # Sample HTML for a mode selection landing page (for a given set)


def handle_flashcard_creation(form):
    set_name = form["set_name"].strip()
    json_input = form["json_input"].strip()
    try:
        data = json.loads(json_input)
    except json.JSONDecodeError:
        return f"<h2 style='color:red;'>❌ Invalid JSON input format.</h2>", 400

    for entry in data:
        if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
            return f"<h2 style='color:red;'>❌ Each entry must have 'phrase', 'pronunciation', and 'meaning'.</h2>", 400

    audio_dir = os.path.join("docs", "static", set_name, "audio")
    output_dir = os.path.join("docs", "output", set_name)
    sets_dir = SETS_DIR / set_name
    sets_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    

    for i, entry in enumerate(data):
        phrase = entry["phrase"]
        filename = f"{i}_{sanitize_filename(phrase)}.mp3"
        filepath = os.path.join(audio_dir, filename)
        if not os.path.exists(filepath):
            tts = gTTS(text=phrase, lang="pl")
            tts.save(filepath)

    with open(os.path.join(sets_dir, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("🛠 Generating practice.html...")
    try:
      generate_practice_html(set_name, data)
    except Exception as e:
      print(f"❌ Failed to generate practice.html: {e}")
      
    generate_flashcard_html(set_name, data)
    generate_practice_html(set_name, data)
    generate_test_html(set_name, data)
    generate_reading_html(set_name, data)
    generate_listening_html(set_name, data)
    update_docs_homepage()
    commit_and_push_changes(f"✅ Add new set: {set_name}")

    return redirect(f"/output/{set_name}/index.html")

def update_docs_homepage():
    docs_path = Path("docs")
    output_path = docs_path / "output"

    if not output_path.exists():
        print("⚠️ No sets in docs/output yet — skipping homepage generation.")
        return

    # Discover sets by checking output folder
    sets = sorted([d.name for d in output_path.iterdir() if d.is_dir()])

    # Detect which modes are present (e.g., flashcards.html, practice.html)
    set_modes = {}
    for s in sets:
        mode_paths = list((output_path / s).glob("*.html"))
        set_modes[s] = [
            p.stem for p in mode_paths if p.stem in {"flashcards", "practice", "reading"}
        ]

    # Load Jinja2 template from templates/index.html
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("index.html")

    # Render it with discovered sets and modes
    rendered_html = template.render(sets=sets, set_modes=set_modes)

    # Write to docs/index.html
    docs_path.mkdir(exist_ok=True)
    with open(docs_path / "index.html", "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print("✅ docs/index.html updated with links to all flashcard sets.")
