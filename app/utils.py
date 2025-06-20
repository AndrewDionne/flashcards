import os, re, json, shutil
from flask import jsonify, redirect, render_template
from gtts import gTTS
import requests

def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9]', '_', text)

def open_browser():
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()

def load_sets_with_counts():
    output_root = "output"
    static_root = "static"
    sets_dict = {}

    if os.path.exists(output_root):
        for set_name in sorted(os.listdir(output_root)):
            set_dir = os.path.join(output_root, set_name)
            if os.path.isdir(set_dir):
                sets_dict[set_name] = {"name": set_name, "count": "?"}

    if os.path.exists(static_root):
        for set_name in sorted(os.listdir(static_root)):
            audio_path = os.path.join(static_root, set_name, "audio")
            if os.path.isdir(audio_path):
                card_count = len([f for f in os.listdir(audio_path) if f.endswith(".mp3")])
                if set_name not in sets_dict:
                    sets_dict[set_name] = {"name": set_name, "count": card_count}
                else:
                    sets_dict[set_name]["count"] = card_count

    return list(sets_dict.values())

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

def handle_flashcard_creation(form):
    set_name = form["set_name"].strip()
    json_input = form["json_input"].strip()
    data = json.loads(json_input)

    for entry in data:
        if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
            return f"<h2 style='color:red;'>❌ Each entry must have 'phrase', 'pronunciation', and 'meaning'.</h2>", 400

    audio_dir = os.path.join("static", set_name, "audio")
    output_dir = os.path.join("output", set_name)
    sets_dir = os.path.join("sets", set_name)
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

    generate_flashcard_html(set_name, data)
    from .git_utils import commit_and_push_changes
    commit_and_push_changes(f"✅ Add new set: {set_name}")

    return redirect(f"/output/{set_name}/flashcards.html")

def generate_flashcard_html(set_name, data):
    # Stub
    pass
