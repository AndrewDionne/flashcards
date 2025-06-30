import os
import json
from pathlib import Path

def generate_practice_html(set_name, data):
    """Generate the practice.html page for a flashcard set."""

    # Ensure output directory
    output_dir = os.path.join("docs", "output", set_name)
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    practice_path = os.path.join(output_dir, "practice.html")
   
    # Prepare data
    cards_json = json.dumps(data, ensure_ascii=False)

    # Practice HTML
    practice_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{set_name} Practice</title>
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

        .home-btn {{
            position: absolute;
            right: 0px;
            top: 0;
            font-size: 1.4em;
            background: none;
            border: none;
            cursor: pointer;
            }}

        .result {{
          font-size: 1.2rem;
          color: #333;
          margin-top: 2rem;
          min-height: 2em;
        }}

        .flash {{
          margin: 10px;
          padding: 12px 20px;
          font-size: 1rem;
          background-color: #007bff;
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          display: inline-block;
        }}

        .flash:hover {{
          background-color: #0056b3;
        }}

        .back {{
          display: block;
          margin-top: 2rem;
          font-size: 0.9rem;
          color: #555;
          text-decoration: none;
        }}

        .back:hover {{
          text-decoration: underline;
        }}
    </style>
</head>
<body>
<h1>{set_name} practice <button class="home-btn" onclick="goHome()">🏠</button></h1>
  
  <button id="startBtn" class="flash">▶️ Start Practice</button>
  <button id="pauseBtn" class="flash" style="margin-left: 1rem;">⏸ Pause</button>

  <div id="result" class="result">🎙 Get ready to practice...</div>

  <script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
<script>
let hasStarted = false;
let paused = false;
let resumeRequested = false;
let index = 0;
let attempts = 0;
let cachedSpeechConfig = null;

const cards = {cards_json};
const setName = "{set_name}";

function sanitizeFilename(text) {{
  return text.replace(/[^a-zA-Z0-9]/g, "_");
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
  audio.play().catch(err => {{
    console.warn("🔇 Autoplay blocked or error:", err);
    callback();
  }});
}}

function speak(text, lang, callback) {{
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.onend = callback;
  utterance.onerror = (e) => {{
    console.warn("🔇 Speech synthesis error:", e.error);
    callback();
  }};

  const voices = speechSynthesis.getVoices();
  if (!voices.length) {{
    speechSynthesis.onvoiceschanged = () => {{
      speechSynthesis.speak(utterance);
    }};
  }} else {{
    speechSynthesis.speak(utterance);
  }}

  setTimeout(() => {{
    if (!speechSynthesis.speaking) {{
      console.warn("⏱ Speech fallback timeout triggered");
      callback();
    }}
  }}, 5000);
}}

async function assessPronunciation(phrase) {{
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
      phrase,
      SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
      SpeechSDK.PronunciationAssessmentGranularity.FullText,
      false
    );
    config.applyTo(recognizer);
    resultDiv.innerHTML = `🎙 Speak: <strong>${{phrase}}</strong>`;
    return new Promise(resolve => {{
      recognizer.recognized = (s, e) => {{
        try {{
          const data = JSON.parse(e.result.json);
          const score = data?.NBest?.[0]?.PronunciationAssessment?.AccuracyScore || 0;
          const feedback = score >= 85
            ? `🌟 Excellent! ${{score.toFixed(1)}}%`
            : score >= 70
            ? `✅ Good! ${{score.toFixed(1)}}%`
            : `⚠️ Needs work: ${{score.toFixed(1)}}%`;
          resultDiv.innerHTML = feedback;
          recognizer.stopContinuousRecognitionAsync();
          resolve(score);
        }} catch (err) {{
          resultDiv.innerHTML = "⚠️ Parsing error.";
          recognizer.stopContinuousRecognitionAsync();
          resolve(0);
        }}
      }};
      recognizer.startContinuousRecognitionAsync();
    }});
  }} catch (err) {{
    console.error("Azure error:", err);
    resultDiv.textContent = "❌ Azure config error.";
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
  if (paused) return;

  const resultDiv = document.getElementById("result");

  if (index >= cards.length) {{
    resultDiv.innerHTML = "✅ Practice complete!";
    return;
  }}

  const entry = cards[index];
  const filename = `${{index}}_${{sanitizeFilename(entry.phrase)}}.mp3`;

  //resultDiv.innerHTML = `🔊 ${{entry.meaning}}`;
  //await new Promise(resolve => speak(entry.meaning, "en-US", resolve));
  //if (paused) return;

  await new Promise(resolve => playAudio(filename, resolve));
  if (paused) return;

  const score = await assessPronunciation(entry.phrase);
  if (paused) return;

  if (score >= 70 || attempts >= 2) {{
    index++;
    attempts = 0;
  }} else {{
    attempts++;
    resultDiv.innerHTML += "<br>🔁 Try again!";
  }}

  setTimeout(() => {{
    if (!paused) runPractice();
  }}, 1800);
}}

function goHome() {{
    const pathParts = window.location.pathname.split("/");
    const repo = pathParts[1];
    window.location.href = window.location.hostname === "andrewdionne.github.io" ? `/${{repo}}/` : "/";
  }}

document.addEventListener("DOMContentLoaded", () => {{
  const startBtn = document.getElementById("startBtn");
  const pauseBtn = document.getElementById("pauseBtn");

  startBtn.addEventListener("click", () => {{
    if (!hasStarted) {{
      hasStarted = true;
      paused = false;
      startBtn.style.display = "none";
      pauseBtn.style.display = "inline-block";
      runPractice();
    }}
  }});

  pauseBtn.addEventListener("click", () => {{
    if (!hasStarted) return;
    paused = !paused;
    pauseBtn.textContent = paused ? "▶️ Resume" : "⏸ Pause";
    if (!paused) {{
      runPractice();
    }}
  }});
}});
</script>

</body>
</html>
"""

    with open(practice_path, "w", encoding="utf-8") as f:
        f.write(practice_html)

    print(f"✅ practice.html generated for: {set_name}")

   