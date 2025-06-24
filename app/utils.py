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
    import os, json
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)
    flashcard_path = os.path.join(output_dir, "flashcards.html")
    practice_path = os.path.join(output_dir, "practice.html")

    cards_json = json.dumps(data)

    # Flashcards Page
    with open(flashcard_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} Flashcards</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0; padding: 20px;
      background-color: #f8f9fa;
      display: flex; flex-direction: column; align-items: center;
    }}
    h1 {{
      font-size: 1.5em;
      margin-bottom: 10px;
      text-align: center;
      width: 100%;
    }}
    .home-btn {{
      position: absolute;
      right: 20px;
      top: 10px;
      font-size: 1.4em;
      background: none;
      border: none;
      cursor: pointer;
    }}
    .card {{
      width: 90%; max-width: 350px; height: 220px;
      perspective: 1000px;
      margin: 20px auto;
    }}
    .card-inner {{
      width: 100%; height: 100%;
      position: relative;
      transition: transform 0.6s;
      transform-style: preserve-3d;
      cursor: pointer;
    }}
    .card.flipped .card-inner {{
      transform: rotateY(180deg);
    }}
    .card-front, .card-back {{
      position: absolute;
      width: 100%; height: 100%;
      backface-visibility: hidden;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
    }}
    .card-front {{ background: #fff; }}
    .card-back {{ background: #e9ecef; transform: rotateY(180deg); flex-direction: column; }}
    .card-back button {{
      margin-top: 12px;
      padding: 6px 12px;
      background-color: #28a745;
      border: none;
      border-radius: 6px;
      color: white;
      cursor: pointer;
    }}
    .nav-buttons {{
      margin-top: 10px;
      display: flex;
      gap: 15px;
    }}
    .practice-btn {{
      margin-top: 10px;
      background-color: #ffc107;
      border: none;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 1em;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <h1>{set_name} Flashcards <button class="home-btn" onclick="goHome()">🏠</button></h1>
  <button class="practice-btn" onclick="window.location.href='practice.html'">🎓 Practice Mode</button>

  <div class="card" id="cardContainer">
    <div class="card-inner" id="cardInner">
      <div class="card-front" id="cardFront"></div>
      <div class="card-back" id="cardBack"></div>
    </div>
  </div>

  <div class="nav-buttons">
    <button id="prevBtn">Previous</button>
    <button id="nextBtn">Next</button>
  </div>

  <audio id="audioPlayer"><source id="audioSource" src="" type="audio/mpeg" /></audio>

  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
  <script>
    const cards = {cards_json};
    const setName = "{set_name}";
    let currentIndex = 0;

    function sanitizeFilename(text) {{
      return text.replace(/[^a-zA-Z0-9]/g, "_");
    }}

    function updateCard() {{
      const entry = cards[currentIndex];
      const filename = `${{currentIndex}}_${{sanitizeFilename(entry.phrase)}}.mp3`;
      document.getElementById("cardFront").textContent = entry.meaning;
      document.getElementById("cardBack").innerHTML = `
        <p>${{entry.phrase}}</p>
        <p><em>${{entry.pronunciation}}</em></p>
        <button onclick="playAudio('${{filename}}')">▶️ Play</button>
        <button onclick="assessPronunciation('${{entry.phrase}}')">🎤 Test</button>
        <div id="pronunciationResult" style="margin-top:10px; font-size:0.9em;"></div>
      `;
      document.getElementById("prevBtn").disabled = currentIndex === 0;
      document.getElementById("nextBtn").disabled = currentIndex === cards.length - 1;
    }}

    function playAudio(filename) {{
      const audio = document.getElementById("audioPlayer");
      const source = document.getElementById("audioSource");
      const repo = window.location.hostname === "andrewdionne.github.io"
        ? window.location.pathname.split("/")[1]
        : "";
      source.src = window.location.hostname === "andrewdionne.github.io"
        ? `/${{repo}}/static/${{setName}}/audio/${{filename}}`
        : `/custom_static/${{setName}}/audio/${{filename}}`;
      audio.load(); audio.play();
    }}

    function assessPronunciation(referenceText) {{
      const resultDiv = document.getElementById("pronunciationResult");
      if (!window.SpeechSDK) {{
        resultDiv.innerHTML = "❌ Azure SDK not loaded."; return;
      }}

      fetch("https://flashcards-5c95.onrender.com/api/token").then(r => r.json()).then(data => {{
        const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
        speechConfig.speechRecognitionLanguage = "pl-PL";
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
        const config = new SpeechSDK.PronunciationAssessmentConfig(referenceText, SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark, SpeechSDK.PronunciationAssessmentGranularity.FullText, false);
        config.applyTo(recognizer);
        recognizer.recognized = (s, e) => {{
          try {{
            const res = JSON.parse(e.result.json);
            const score = res.NBest[0].PronunciationAssessment.AccuracyScore.toFixed(1);
            resultDiv.innerHTML = score >= 85 ? `🌟 ${{score}}%` : score >= 70 ? `✅ ${{score}}%` : `⚠️ ${{score}}%`;
          }} catch (err) {{
            resultDiv.innerHTML = "⚠️ Could not assess.";
          }}
          recognizer.stopContinuousRecognitionAsync();
        }};
        recognizer.startContinuousRecognitionAsync();
      }});
    }}

    document.getElementById("cardContainer").addEventListener("click", (e) => {{
      if (!e.target.closest("button")) {{
        document.getElementById("cardContainer").classList.toggle("flipped");
      }}
    }});

    document.getElementById("prevBtn").onclick = () => {{ if (currentIndex > 0) {{ currentIndex--; updateCard(); }} }};
    document.getElementById("nextBtn").onclick = () => {{ if (currentIndex < cards.length - 1) {{ currentIndex++; updateCard(); }} }};

    function goHome() {{
      const pathParts = window.location.pathname.split("/");
      const repo = pathParts[1];
      window.location.href = window.location.hostname === "andrewdionne.github.io" ? `/${{repo}}/` : "/";
    }}

    updateCard();
  </script>
</body>
</html>
""")

    # Practice Page (just a placeholder fix for now)
    with open(practice_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{set_name} Practice</title></head>
<body>
<h1>{set_name} Practice Mode</h1>
<script>
alert("🚧 Practice mode still needs script-based layout. Coming next.");
</script>
</body></html>""")

    print(f"✅ Flashcard + practice HTML generated for {set_name}")
    

    #with open(flashcard_path, "w", encoding="utf-8") as f:
        #f.write(shared_head + flashcard_body)

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
