import os, re, json, shutil
from flask import jsonify, redirect, render_template
from gtts import gTTS
import requests
from pathlib import Path


def sanitize_filename(text):
    return re.sub(r'[^a-zA-Z0-9]', '_', text)

def open_browser():
    import webbrowser, threading
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5000")).start()

def load_sets_with_counts():
    output_root = os.path.join("docs", "output")
    static_root = os.path.join("docs", "static")
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
                card_count = len([
                    f for f in os.listdir(audio_path)
                    if f.endswith(".mp3")
                ])
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

    def sanitize_filename(text):
        import re
        return re.sub(r'[^a-zA-Z0-9]', '_', text)

def generate_flashcard_html(set_name, data):
    import os, json
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)
    flashcard_html_path = os.path.join(output_dir, "flashcards.html")
    practice_html_path = os.path.join(output_dir, "practice.html")

    cards_json = json.dumps(data)

    # Shared CSS + HTML
    shared_head = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{set_name} Flashcards</title>
    <style>
        body {{ font-family: sans-serif; padding: 2rem; background: #f4f4f4; text-align: center; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 1rem; }}
        button {{ font-size: 1rem; padding: 10px 20px; margin: 10px; border-radius: 6px; border: none; cursor: pointer; }}
        .flash {{ background-color: #007bff; color: white; }}
        .practice {{ background-color: #ffc107; color: black; }}
        .result {{ margin-top: 1rem; font-size: 1.1rem; }}
    </style>
</head>
<body>
    <h1>{set_name} Flashcards</h1>
    <div id=\"main\"></div>
    <script src=\"https://aka.ms/csspeech/jsbrowserpackageraw\"></script>
    <script>
        const cards = {cards_json};
        const setName = \"{set_name}\";
        const repo = window.location.hostname === "andrewdionne.github.io" ? window.location.pathname.split("/")[1] : "";
        const basePath = window.location.hostname === "andrewdionne.github.io" ? `/${repo}/` : "/";

        function sanitizeFilename(text) {{ return text.replace(/[^a-zA-Z0-9]/g, '_'); }}
        function audioUrl(index, phrase) {{ return `${basePath}static/${setName}/audio/${index}_${sanitizeFilename(phrase)}.mp3`; }}
    </script>
"""

    # Flashcards.html
    flashcard_body = f"""
    <button class=\"flash\" onclick=\"window.location.href='practice.html'\">🎓 Practice Mode</button>
    <div id=\"card\"></div>
    <audio id=\"audioPlayer\" preload=\"auto\"></audio>
    <script>
        let currentIndex = 0;
        function updateCard() {{
            const card = cards[currentIndex];
            const cardDiv = document.getElementById("card");
            cardDiv.innerHTML = `
                <div>
                    <p><strong>English:</strong> ${card.meaning}</p>
                    <p><strong>Polish:</strong> ${card.phrase}</p>
                    <p><em>${card.pronunciation}</em></p>
                    <button onclick=\"playAudio(currentIndex)\">▶️ Play Audio</button>
                    <button onclick=\"assessPronunciation(card.phrase)\">🎤 Test Pronunciation</button>
                    <div id='pronunciationResult' class='result'></div>
                </div>
            `;
        }}

        function playAudio(index) {{
            const audio = document.getElementById("audioPlayer");
            audio.src = audioUrl(index, cards[index].phrase);
            audio.play();
        }}

        async function assessPronunciation(referenceText) {{
            const resultDiv = document.getElementById("pronunciationResult");
            if (!window.SpeechSDK) return resultDiv.textContent = "Azure SDK not loaded.";
            const res = await fetch("https://flashcards-5c95.onrender.com/api/token");
            const {{ token, region }} = await res.json();
            const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
            speechConfig.speechRecognitionLanguage = "pl-PL";
            const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
            const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
            const config = new SpeechSDK.PronunciationAssessmentConfig(referenceText, SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark, SpeechSDK.PronunciationAssessmentGranularity.FullText, false);
            config.applyTo(recognizer);

            recognizer.recognizeOnceAsync(result => {{
                const data = JSON.parse(result.json);
                const score = data.NBest?.[0]?.PronunciationAssessment?.AccuracyScore || 0;
                resultDiv.textContent = score >= 85 ? `🌟 Excellent! Score: ${score.toFixed(1)}%` :
                                        score >= 70 ? `✅ Good! Score: ${score.toFixed(1)}%` :
                                                    `⚠️ Try again: ${score.toFixed(1)}%`;
            }});
        }}

        updateCard();
    </script>
</body>
</html>
"""

    # Practice.html
    practice_body = f"""
    <button class=\"flash\" onclick=\"window.location.href='flashcards.html'\">⬅️ Back to Flashcards</button>
    <div id='result' class='result'></div>
    <script>
        let index = 0;
        let attempts = 0;
        let cachedSpeechConfig = null;

        async function speak(text, lang, cb) {{
            const u = new SpeechSynthesisUtterance(text);
            u.lang = lang;
            u.onend = cb;
            speechSynthesis.speak(u);
        }}

        async function playThenTest(card) {{
            const audio = new Audio(audioUrl(index, card.phrase));
            audio.onended = async () => {{
                const score = await assess(card.phrase);
                const resultDiv = document.getElementById("result");
                if (score >= 70 || attempts >= 2) {{
                    resultDiv.textContent = `✅ ${card.phrase}: ${score.toFixed(1)}%`;
                    index++;
                    attempts = 0;
                    setTimeout(practiceNext, 1000);
                }} else {{
                    attempts++;
                    resultDiv.textContent = `🔁 Try again (${attempts}/3)`;
                    setTimeout(() => playThenTest(card), 1000);
                }}
            }};
            audio.play();
        }}

        async function assess(ref) {{
            if (!cachedSpeechConfig) {{
                const res = await fetch("https://flashcards-5c95.onrender.com/api/token");
                const data = await res.json();
                cachedSpeechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
                cachedSpeechConfig.speechRecognitionLanguage = "pl-PL";
            }}
            const recognizer = new SpeechSDK.SpeechRecognizer(cachedSpeechConfig, SpeechSDK.AudioConfig.fromDefaultMicrophoneInput());
            const config = new SpeechSDK.PronunciationAssessmentConfig(ref, SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark, SpeechSDK.PronunciationAssessmentGranularity.FullText, false);
            config.applyTo(recognizer);

            return new Promise(resolve => recognizer.recognizeOnceAsync(r => {{
                const score = JSON.parse(r.json).NBest?.[0]?.PronunciationAssessment?.AccuracyScore || 0;
                resolve(score);
            }}));
        }}

        async function practiceNext() {{
            if (index >= cards.length) return document.getElementById("result").textContent = "🎉 Practice Complete!";
            const card = cards[index];
            speak(card.meaning, "en", () => speak(card.phrase, "pl", () => playThenTest(card)));
        }}

        practiceNext();
    </script>
</body>
</html>
"""

    with open(flashcard_html_path, "w", encoding="utf-8") as f:
        f.write(shared_head + flashcard_body)

    with open(practice_html_path, "w", encoding="utf-8") as f:
        f.write(shared_head + practice_body)

    print(f"✅ Generated HTML for set: {set_name}")



def update_docs_homepage():
    docs_path = Path("docs")
    output_path = docs_path / "output"

    if not output_path.exists():
        print("⚠️ No sets in docs/output yet — skipping homepage generation.")
        return

    sets = sorted([d.name for d in output_path.iterdir() if d.is_dir()])
    links = "\n".join(
        f'<div class="card-link"><a href="output/{s}/flashcards.html">{s}</a></div>'
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
    homepage_file = docs_path / "index.html"
    homepage_file.write_text(homepage_html, encoding="utf-8")

    print("✅ docs/index.html updated with styled homepage.")




 # Write to disk
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html + html_script)
