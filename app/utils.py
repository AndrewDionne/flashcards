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

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9]', '_', text)

def open_browser():
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()

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

def delete_set(set_name):
    from .git_utils import commit_and_push_changes

    output_dir = Path("docs/output") / set_name
    static_dir = Path("docs/static") / set_name
    sets_dir = Path("docs/sets") / set_name

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
def generate_mode_landing_page(set_name):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{set_name} - Choose Learning Mode</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: sans-serif;
            background: #f8f9fa;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{
            font-size: 1.8rem;
            margin-bottom: 2rem;
        }}
        .mode-buttons {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 1rem;
        }}
        .mode-button {{
            padding: 1rem 1.5rem;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 1rem;
            transition: background 0.3s;
        }}
        .mode-button:hover {{
            background: #0056b3;
        }}
        .home-link {{
            margin-top: 2rem;
            text-decoration: none;
            font-size: 0.9rem;
            color: #555;
        }}
    </style>
</head>
<body>
    <h1>{set_name} – Choose Your Learning Mode</h1>
    <div class="mode-buttons">
        <a class="mode-button" href="flashcards.html">📚 Flashcards</a>
        <a class="mode-button" href="practice.html">🎤 Practice</a>
        <a class="mode-button" href="reading.html">📖 Reading</a>
        <a class="mode-button" href="listening.html">🎧 Listening</a>
        <a class="mode-button" href="test.html">🎓 Test Yourself</a>
    </div>
    <a class="home-link" href="../../landing.html">← Back to All Sets</a>
</body>
</html>
"""
    output_path = Path("docs/output") / set_name / "landing.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return str(output_path)

def handle_flashcard_creation(form):
    set_name = form["set_name"].strip()
    json_input = form["json_input"].strip()
    data = json.loads(json_input)

    for entry in data:
        if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
            return f"<h2 style='color:red;'>❌ Each entry must have 'phrase', 'pronunciation', and 'meaning'.</h2>", 400

    audio_dir = os.path.join("docs", "static", set_name, "audio")
    output_dir = os.path.join("docs", "output", set_name)
    sets_dir = os.path.join("docs", "sets", set_name)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(sets_dir, exist_ok=True)

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
    generate_mode_landing_page(set_name)
    generate_reading_homepage(set_name, data)
    generate_listening_homepage(set_name, data)
    update_docs_homepage()
    commit_and_push_changes(f"✅ Add new set: {set_name}")

    return redirect(f"/output/{set_name}/landing.html")

def update_docs_homepage():
    docs_path = Path("docs")
    output_path = docs_path / "output"

    if not output_path.exists():
        print("⚠️ No sets in docs/output yet — skipping homepage generation.")
        return

    sets = sorted([d.name for d in output_path.iterdir() if d.is_dir()])
    links = "\n".join(
        f'<div class="card-link"><a href="output/{s}/flashcards.html">{s}</a> | <a href="output/{s}/practice.html">Practice</a></div>'
        for s in sets
    )

    homepage_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>📘 Flashcard Sets</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0;
      padding: 20px;
      background-color: #f8f9fa;
      color: #333;
    }}
    h1 {{
      font-size: 1.8em;
      text-align: center;
      margin-bottom: 30px;
    }}
    .set-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 15px;
      max-width: 900px;
      margin: 0 auto;
    }}
    .card-link {{
      background-color: white;
      padding: 20px;
      border-radius: 12px;
      text-align: center;
      font-size: 1.1em;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
      transition: transform 0.2s;
    }}
    .card-link a {{
      text-decoration: none;
      color: #007bff;
    }}
    .card-link:hover {{
      transform: scale(1.03);
    }}
    footer {{
      text-align: center;
      margin-top: 40px;
      font-size: 0.9em;
      color: #888;
    }}
  </style>
</head>
<body>
  <h1>📘 Polish Flashcard Sets</h1>
  <div class="set-grid">
    {links}
  </div>
  <footer>Made with ❤️ for language learning</footer>
</body>
</html>
    """

    docs_path.mkdir(exist_ok=True)
    with open(docs_path / "index.html", "w", encoding="utf-8") as f:
        f.write(homepage_html)

    print("✅ docs/index.html updated with links to all flashcard sets.")
