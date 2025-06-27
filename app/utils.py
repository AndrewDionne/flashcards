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


def generate_listening_homepage(set_name):
    from pathlib import Path

    listening_path = Path("docs/output") / set_name / "listening"
    listening_path.mkdir(parents=True, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} – Listening Mode</title>
    <h1>🎧 Listening Mode – {set_name}</h1>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f9f9f9;
            padding: 2rem;
            text-align: center;
        }}
        h1 {{
            font-size: 1.6rem;
            margin-bottom: 1rem;
        }}
        .info {{
            font-size: 1rem;
            color: #555;
            margin-bottom: 2rem;
        }}
        .action {{
            display: inline-block;
            padding: 12px 20px;
            background-color: #28a745;
            color: white;
            font-size: 1rem;
            text-decoration: none;
            border-radius: 8px;
        }}
        .back {{
            display: block;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #555;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>📖 listening Mode – {set_name}</h1>
    <div class="info">Practice listening to full Polish phrases and sentances and respond.</div>
    <a class="action" href="../listening.html">🔁 Start Listening Practice</a>
    <a class="back" href="../index.html">← Back to Mode Selection</a>
</body>
</html>
"""

    with open(listening_path / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Reading mode homepage generated at: {listening_path / 'index.html'}")
    
   
def generate_reading_homepage(set_name):
    from pathlib import Path

    reading_path = Path("docs/output") / set_name / "reading"
    reading_path.mkdir(parents=True, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} – Reading Mode</title>
    <h1>📖 Reading Mode – {set_name}</h1>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f9f9f9;
            padding: 2rem;
            text-align: center;
        }}
        h1 {{
            font-size: 1.6rem;
            margin-bottom: 1rem;
        }}
        .info {{
            font-size: 1rem;
            color: #555;
            margin-bottom: 2rem;
        }}
        .action {{
            display: inline-block;
            padding: 12px 20px;
            background-color: #28a745;
            color: white;
            font-size: 1rem;
            text-decoration: none;
            border-radius: 8px;
        }}
        .back {{
            display: block;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #555;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>📖 Reading Mode – {set_name}</h1>
    <div class="info">Practice reading full Polish phrases and get pronunciation feedback.</div>
    <a class="action" href="../reading.html">🔁 Start Reading Practice</a>
    <a class="back" href="../index.html">← Back to Mode Selection</a>
</body>
</html>
"""

    with open(reading_path / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Reading mode homepage generated at: {reading_path / 'index.html'}")


def generate_test_homepage(set_name):
    from pathlib import Path

    test_path = Path("docs/output") / set_name / "test"
    test_path.mkdir(parents=True, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} – Test Yourself</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f9f9f9;
            padding: 2rem;
            text-align: center;
        }}
        h1 {{
            font-size: 1.6rem;
            margin-bottom: 1rem;
        }}
        .info {{
            font-size: 1rem;
            color: #555;
            margin-bottom: 2rem;
        }}
        .action {{
            display: inline-block;
            padding: 12px 20px;
            background-color: #ffc107;
            color: black;
            font-size: 1rem;
            text-decoration: none;
            border-radius: 8px;
        }}
        .back {{
            display: block;
            margin-top: 2rem;
            font-size: 0.9rem;
            color: #555;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>🎓 Test Yourself – {set_name}</h1>
    <div class="info">Try quizzes and challenges across flashcards, pronunciation, reading, and listening modes.</div>
    <a class="action" href="../flashcards.html">🚀 Start Test</a>
    <a class="back" href="../index.html">← Back to Mode Selection</a>
</body>
</html>
"""

    with open(test_path / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Test mode homepage generated at: {test_path / 'index.html'}")

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
    generate_mode_landing_page(set_name)
    generate_reading_homepage(set_name)
    generate_listening_homepage(set_name)
    generate_test_homepage(set_name)
    update_docs_homepage()
    commit_and_push_changes(f"✅ Add new set: {set_name}")

    return redirect(f"/output/{set_name}/landing.html")

def generate_flashcard_html(set_name, data):
    import os, json

    # Ensure output directory
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    flashcard_path = os.path.join(output_dir, "flashcards.html")
    practice_path = os.path.join(output_dir, "practice.html")

    # Prepare data
    cards_json = json.dumps(data, ensure_ascii=False)

    # Flashcard HTML
    flashcard_html = f"""<!DOCTYPE html>
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
            justify-content: flex-start;
            min-height: 100vh;
            box-sizing: border-box;
            overflow-x: hidden; /* prevents weird horizontal scroll on iPhone */
        }}
        h1 {{
            font-size: 1.5em;
            margin-bottom: 20px;
            position: relative;
            width: 100%;
            text-align: center;
        }}
        
        .home-btn {{
            position: absolute;
            right: 0px;
            top: 0;
            font-size: 1.4em;
            background: none;
            border: none;
            cursor: pointer;
            }}

        .card {{
            width: 90%;
            max-width: 350px;
            height: 220px;
            perspective: 1000px;
            margin-top: 20px;
            margin-bottom: 20px;
            margin-left: auto;
            margin-right: auto;
            box-sizing: border-box;
        }}

        .card-inner {{
            width: 100%; 
            height: 100%;
            position: relative;
            transition: transform 0.6s;
            transform-origin: center;
            transform-style: preserve-3d;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: center;
            align-items: center;
            border-radius: 12px;

        }}
        .card.flipped .card-inner {{
            transform: rotateY(180deg);
        }}
        .card-front, .card-back {{
            position: absolute;
            width: 100%; height: 100%;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            backface-visibility: hidden;
        }}
        .card-front {{
            background: #ffffff;
            font-size: 1.1em;
            font-weight: normal;
            text-align: center;
            word-wrap: break-word;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .card-back {{
            min-height: 100%;
            background: #e9ecef;
            transform: rotateY(180deg);
            flex-direction: column;
            font-size: 1.1em;
            text-align: center;
            word-wrap: break-word;
            text-align: center;
            display: flex;
            flex-direction: column
            justify-content: center;
            align-items: center;
        }}
        .card-back button {{
            margin-top: auto; /* Pushes it to the bottom of the column */
            margin-bottom: 20px; /* Optional spacing from bottom */
            padding: 8px 16px;
            font-size: 1em;
            background-color: #28a745;
            border: none;
            border-radius: 8px;
            color: white;
            cursor: pointer;
        }}
        .nav-buttons {{
            display: flex;
            flex-direction: row;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-top: 20px;
        }}

        .nav-button {{
        padding: 6px 12px;
            font-size: 1em;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            width: 100px;
            height: 30px;
            cursor: pointer;
        }}
        .play-audio-button {{
            margin-bottom: 10px;
            padding: 4px 10px;
            font-size: 0.9em;
            background-color: #28a745;
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            width: auto; /* or a fixed smaller width */
            height: auto;
        }}

        button {{
            border: none;
            cursor: pointer;
        
        }}
        .nav-button:disabled {{
            background-color: #aaa;
            cursor: default;
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
        speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000");
        speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000");
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
"""

    practice_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{set_name} Practice</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        body {{
            font-family: sans-serif;
            background-color: #f0f0f0;
            padding: 20px;
            text-align: center;
        }}
        .flash {{
            margin: 10px;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }}
        .result {{
            font-size: 1.2em;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>{set_name} Practice Mode</h1>
    <button class="flash" onclick="window.location.href='flashcards.html'">⬅️ Back to Flashcards</button>
    <div id="result" class="result">🎙 Get ready to practice...</div>

<script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
<script>
const cards = {cards_json};
const setName = "{set_name}";
let index = 0;
let attempts = 0;
let cachedSpeechConfig = null;

function sanitize(text) {{
  return text.replace(/[^a-zA-Z0-9]/g, "_");
}}

function speak(text, lang, callback) {{
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.onend = callback;
  speechSynthesis.speak(utterance);
}}

function playAudio(filename, callback) {{
  const repo = window.location.hostname === "andrewdionne.github.io"
    ? window.location.pathname.split("/")[1]
    : "";

  const path = window.location.hostname === "andrewdionne.github.io"
    ? `/${{repo}}/static/${{setName}}/audio/${{filename}}`
    : `/custom_static/${{setName}}/audio/${{filename}}`;

  const audio = new Audio(path);
  audio.onended = callback;
  audio.onerror = () => {{
    console.warn("⚠️ Audio failed to play:", path);
    callback();
  }};
  audio.play();

  setTimeout(() => {{
    if (!audio.ended) {{
      audio.pause();
      callback();
    }}
  }}, 5000);
}}

function adjustScore(score) {{
  if (score = 100) return score ;
  if (score <= 99) return score - 9;
  if (score <= 80) return score - 10;
  return score - 12;
}}

async function assessPronunciation(referenceText) {{
  const resultDiv = document.getElementById("result");

  if (!window.SpeechSDK) {{
    resultDiv.textContent = "❌ Azure SDK not loaded.";
    return 0;
  }}

  try {{
    const speechConfig = await getSpeechConfig();
    const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
    const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

    const config = new SpeechSDK.PronunciationAssessmentConfig(
      referenceText,
      SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
      SpeechSDK.PronunciationAssessmentGranularity.FullText,
      false
    );
    config.applyTo(recognizer);

    resultDiv.innerHTML = `🎙 Speak: <strong>${{referenceText}}</strong>`;

    return new Promise(resolve => {{
      recognizer.recognized = (s, e) => {{
        try {{
          const data = JSON.parse(e.result.json);
          const score = data?.NBest?.[0]?.PronunciationAssessment?.AccuracyScore || 0;
          let feedback = score >= 85
            ? `💯 Excellent! ${{score.toFixed(1)}}%`
            : score >= 70
            ? `✅ Good! ${{score.toFixed(1)}}%`
            : `⚠️ Needs work: ${{score.toFixed(1)}}%`;
          resultDiv.innerHTML = feedback;
          recognizer.stopContinuousRecognitionAsync();
          resolve(score);
        }} catch (err) {{
          resultDiv.textContent = "⚠️ Recognition error.";
          recognizer.stopContinuousRecognitionAsync();
          resolve(0);
        }}
      }};

      recognizer.startContinuousRecognitionAsync();
    }});
  }} catch (err) {{
    console.error("Azure error:", err);
    document.getElementById("result").textContent = "❌ Error contacting Azure.";
    return 0;
  }}
}}

async function getSpeechConfig() {{
  if (cachedSpeechConfig) return cachedSpeechConfig;
  const res = await fetch("https://flashcards-5c95.onrender.com/api/token");
  const data = await res.json();
  const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
  speechConfig.speechRecognitionLanguage = "pl-PL";
  speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "1500");
  speechConfig.setProperty(SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000");
  cachedSpeechConfig = speechConfig;
  return speechConfig;
}}

async function runPractice() {{
  const resultDiv = document.getElementById("result");

  if (index >= cards.length) {{
    resultDiv.innerHTML = "✅ Practice complete!";
    return;
  }}

  const entry = cards[index];
  const filename = `${{index}}_${{sanitize(entry.phrase)}}.mp3`;

  resultDiv.innerHTML = `🔊 ${{entry.meaning}}...`;

  speak(entry.meaning, "en-US", () => {{
    resultDiv.innerHTML = "🎧 Playing audio...";
    playAudio(filename, async() => {{
      //resultDiv.innerHTML = "🗣️ Now say: " + entry.phrase;
      //speak(entry.phrase, "pl-PL", async () => {{
        const score = await assessPronunciation(entry.phrase);

        if (score >= 70 || attempts >= 2) {{
          index++;
          attempts = 0;
          setTimeout(runPractice, 1500);
        }} else {{
          attempts++;
          resultDiv.innerHTML += "<br>🔁 Trying again...";
          setTimeout(runPractice, 1800);
        }}
      }});
    }});
  }}


document.addEventListener("DOMContentLoaded", runPractice);
</script>

</body>
</html>
""".format(set_name=set_name, cards_json=cards_json)

    with open(flashcard_path, "w", encoding="utf-8") as f:
        f.write(flashcard_html)

    with open(practice_path, "w", encoding="utf-8") as f:
        f.write(practice_html)

    print(f"✅ Generated flashcards and practice pages for: {set_name}")

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
