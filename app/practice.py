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

function sanitizeFilename(text) {{
  return text.replace(/[^a-zA-Z0-9]/g, "_");
}}

function speak(text, lang, callback) {{
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.onend = callback;
  speechSynthesis.speak(utterance);
}}
document.addEventListener("DOMContentLoaded", () => {{
    if (!window.SpeechSDK) {{
        console.error("❌ Azure Speech SDK failed to load.");
    }} else {{
        console.log("✅ Azure Speech SDK loaded successfully.");
    }}
}});
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

    with open(practice_path, "w", encoding="utf-8") as f:
        f.write(practice_html)

    print(f"✅ practice.html generated for: {set_name}")
   