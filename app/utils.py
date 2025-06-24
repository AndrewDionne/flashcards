import os, re, json, shutil
from flask import jsonify, redirect, render_template
from gtts import gTTS
import requests
from pathlib import Path
from .git_utils import commit_and_push_changes

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

    generate_flashcard_html(set_name, data)
    update_docs_homepage()
    commit_and_push_changes(f"✅ Add new set: {set_name}")

    return redirect(f"/output/{set_name}/flashcards.html")

def generate_flashcard_html(set_name, data):
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)
    flashcard_html_path = os.path.join(output_dir, "flashcards.html")
    practice_html_path = os.path.join(output_dir, "practice.html")

    cards_json = json.dumps(data)

    shared_head = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <title>{set_name} Flashcards</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <style>
        body {{ font-family: sans-serif; padding: 2rem; }}
        .card-link {{ margin-bottom: 1rem; }}
        .flash {{ margin-bottom: 20px; }}
        .result {{ margin-top: 20px; font-weight: bold; }}
    </style>
</head>
<body>
"""

    flashcard_body = f"""
<h1>{set_name} Flashcards</h1>
<p><a href=\"practice.html\">🎓 Practice Mode</a></p>
<ul>
    {''.join(f'<li><strong>{{entry["meaning"]}}</strong>: {{entry["phrase"]}} <em>({{entry["pronunciation"]}})</em></li>' for entry in data)}
</ul>
"""

    practice_body = f"""
<button class=\"flash\" onclick=\"window.location.href='flashcards.html'\">⬅️ Back to Flashcards</button>
<div id='result' class='result'></div>
<script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
<script>
    const cards = {cards_json};
    let index = 0;
    let tries = 0;
    let cachedSpeechConfig = null;

    function speak(text, lang, cb) {{
        const msg = new SpeechSynthesisUtterance(text);
        msg.lang = lang;
        msg.onend = cb;
        speechSynthesis.speak(msg);
    }}

    function playAudio(index, cb) {{
        const phrase = cards[index].phrase;
        const filename = `${{index}}_${{phrase.replace(/[^a-zA-Z0-9]/g, '_')}}.mp3`;
        const audio = new Audio();
        const repo = window.location.pathname.split("/")[1];
        const basePath = window.location.hostname === "andrewdionne.github.io" ? `/${{window.location.pathname.split("/")[1]}}/` : "/";
        audio.src = `${{basePath}}static/${{set_name}}/audio/${{filename}}`;
        audio.onended = cb;
        audio.play();
    }}

    async function getSpeechConfig() {{
        if (cachedSpeechConfig) return cachedSpeechConfig;
        const res = await fetch("https://flashcards-5c95.onrender.com/api/token");
        const data = await res.json();
        const config = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
        config.speechRecognitionLanguage = "pl-PL";
        cachedSpeechConfig = config;
        return config;
    }}

    async function assess(text) {{
        const resultDiv = document.getElementById("result");
        const config = await getSpeechConfig();
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        const recognizer = new SpeechSDK.SpeechRecognizer(config, audioConfig);
        const assessConfig = new SpeechSDK.PronunciationAssessmentConfig(text, SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark, SpeechSDK.PronunciationAssessmentGranularity.FullText, false);
        assessConfig.applyTo(recognizer);

        return new Promise(resolve => {{
            recognizer.recognized = (s, e) => {{
                let score = 0;
                try {{
                    const data = JSON.parse(e.result.json);
                    score = data.NBest[0].PronunciationAssessment.AccuracyScore;
                }} catch {{}}
                recognizer.stopContinuousRecognitionAsync();
                resolve(score);
            }};
            recognizer.startContinuousRecognitionAsync();
        }});
    }}

    async function run() {{
        if (index >= cards.length) {{
            document.getElementById("result").innerText = "🎉 Practice complete!";
            return;
        }}
        const card = cards[index];
        speak(card.meaning, "en", () => {{
            playAudio(index, async () => {{
                const score = await assess(card.phrase);
                if (score >= 70 || tries >= 2) {{
                    index++;
                    tries = 0;
                }} else {{
                    tries++;
                }}
                run();
            }});
        }});
    }}

    run();
</script>
</body>
</html>
"""

    with open(flashcard_html_path, "w", encoding="utf-8") as f:
        f.write(shared_head + flashcard_body)

    with open(practice_html_path, "w", encoding="utf-8") as f:
        f.write(shared_head + practice_body)

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
<html>
<head>
    <meta charset="UTF-8">
    <title>Flashcard Sets</title>
    <style>
        body {{ font-family: sans-serif; padding: 2rem; }}
        .card-link {{ margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <h1>📘 Flashcard Sets</h1>
    {links}
</body>
</html>
"""

    docs_path.mkdir(exist_ok=True)
    with open(docs_path / "index.html", "w", encoding="utf-8") as f:
        f.write(homepage_html)

    print("✅ docs/index.html updated with links to all flashcard sets.")
