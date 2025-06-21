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
    output_dir = os.path.join("output", set_name)
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, "flashcards.html")

    # HTML head + card layout
    full_html = f"""
<!DOCTYPE html>
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
    <h1>
    {set_name} Flashcards
        <button class="home-btn" onclick="goHome()">🏠</button>
    </h1>
    <div class="card" id="cardContainer">
        <div class="card-inner" id="cardInner">
            <div class="card-front" id="cardFront"></div>
            <div class="card-back" id="cardBack"></div>
        </div>
    </div>
    <div class="nav-buttons">
        <button id="prevBtn" class="nav-button">Previous</button>
        <button id="nextBtn" class="nav-button">Next</button>
    
    <audio id="audioPlayer" preload="auto">
        <source id="audioSource" src="" type="audio/mpeg" />
        Your browser does not support the audio element.
    </audio>
"""
        # JavaScript part (add after HTML body layout)
    html_script = f"""
<script src="https://aka.ms/csspeech/jsbrowserpackageraw"></script>
<script>
    const cards = {json.dumps(data)};
    const setName = "{set_name}";
    let currentIndex = 0;
    const cardFront = document.getElementById("cardFront");
    const cardBack = document.getElementById("cardBack");
    const card = document.getElementById("cardContainer");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");

    function sanitizeFilename(text) {{
        return text.replace(/[^a-zA-Z0-9]/g, "_");
    }}

    function updateCard() {{
        const entry = cards[currentIndex];
        const filename = `${{currentIndex}}_${{sanitizeFilename(entry.phrase)}}.mp3`;
        cardFront.textContent = entry.meaning;
        cardBack.innerHTML = `
            <p>${{entry.phrase}}</p>
            <p><em>${{entry.pronunciation}}</em></p>
            <button class="play-audio-button" onclick="playAudio('${{filename}}')">▶️ Play Audio</button>
            <button class="play-audio-button" onclick="assessPronunciation('${{entry.phrase}}')">🎤 Test Pronunciation</button>
            <div id="pronunciationResult" style="margin-top: 10px; font-size: 0.9em;"></div>
            <audio id="audioPlayer" preload="auto">
                <source id="audioSource" src="" type="audio/mpeg" />
                Your browser does not support the audio element.
            </audio>
        `;
        prevBtn.disabled = currentIndex === 0;
        nextBtn.disabled = currentIndex === cards.length - 1;
        card.classList.remove("flipped");
    }}
        

        function goHome() {{
        const pathParts = window.location.pathname.split("/");
        const repo = pathParts[1]; // repo name comes right after domain
        if (window.location.hostname === "andrewdionne.github.io" && repo) {{
        window.location.href = `/${{repo}}/`;
        }} else {{
            window.location.href = "/";
        }}
}}
        function playAudio(filename) {{
        const audio = document.getElementById("audioPlayer");
        const source = document.getElementById("audioSource");

        let newSrc = "";

        if (window.location.hostname === "andrewdionne.github.io") {{
        // GitHub Pages path: /WSPOL-Names/sets/setName/audio/filename
            const repo = window.location.pathname.split("/")[1]; // e.g., WSPOL-Names
            newSrc = `/${{repo}}/sets/${{setName}}/audio/${{filename}}`;
    }} else {{
        // Local Flask path: /static/setName/audio/filename
            newSrc = `/static/${{setName}}/audio/${{filename}}`;
    }}

    console.log("Playing:", newSrc);
    source.src = newSrc;
    audio.load();
    audio.currentTime = 0;
    audio.play();
}}


    prevBtn.addEventListener("click", () => {{
        if (currentIndex > 0) {{
            currentIndex--;
            updateCard();
        }}
    }});

    nextBtn.addEventListener("click", () => {{
        if (currentIndex < cards.length - 1) {{
            currentIndex++;
            updateCard();
        }}
    }});

    card.addEventListener("click", (event) => {{
        if (
            event.target.tagName.toLowerCase() === 'audio' ||
            event.target.closest('audio') ||
            event.target.tagName.toLowerCase() === 'button'
        ) {{
            return;
        }}
        card.classList.toggle("flipped");
    }});

    updateCard();


    async function assessPronunciation(referenceText) {{
        let cachedSpeechConfig = null;
        async function getSpeechConfig() {{
            if (cachedSpeechConfig) return cachedSpeechConfig;

            const BASE_URL = "https://flashcards-5c95.onrender.com"; // ✅ hardcoded Render backend

            const res = await fetch(`${{BASE_URL}}/api/token`);
            const data = await res.json();

            if (!data.token) {{
                throw new Error("Failed to fetch speech token");
            }}

            const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
            speechConfig.speechRecognitionLanguage = "pl-PL";
            cachedSpeechConfig = speechConfig;
            return speechConfig;
        }}

        
        const resultDiv = document.getElementById("pronunciationResult");

        if (!window.SpeechSDK) {{
            resultDiv.textContent = "❌ Azure Speech SDK not loaded.";
            return;
        }}

        try {{
            const speechConfig = await getSpeechConfig();
            const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();

            const pronunciationConfig = new SpeechSDK.PronunciationAssessmentConfig(
                referenceText,
                SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
                SpeechSDK.PronunciationAssessmentGranularity.Phoneme,
                true
            );

            const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
            pronunciationConfig.applyTo(recognizer);

            resultDiv.textContent = "🎙 Listening...";

            recognizer.recognizeOnceAsync(result => {{
                console.log("Azure Recognition Result:", result);

                if (result.reason !== SpeechSDK.ResultReason.RecognizedSpeech) {{
                    resultDiv.textContent = "❌ Speech not recognized. Try again.";
                    recognizer.close();
                    return;
                }}

                if (!result.json) {{
                    resultDiv.textContent = "⚠️ No response from Azure.";
                    recognizer.close();
                    return;
                }}

                try {{
                    const data = JSON.parse(result.json);
                    const nbest = data.NBest;

                    if (!nbest || !nbest.length || !nbest[0].PronunciationAssessment) {{
                        resultDiv.textContent = "❌ No valid pronunciation result.";
                    }} else {{
                        const score = nbest[0].PronunciationAssessment.AccuracyScore;
                        resultDiv.innerHTML = `✅ Accuracy Score: <strong>${{score.toFixed(1)}}%</strong>`;
                    }}
                }} catch (e) {{
                    console.error("Error parsing Azure JSON:", e);
                    resultDiv.textContent = "⚠️ Error parsing response.";
                }}

                recognizer.close();
            }});
        }} catch (error) {{
            console.error("Azure token or recognition error:", error);
            resultDiv.textContent = "❌ Could not assess pronunciation.";
        }}
    }}

    document.addEventListener("keydown", (event) => {{
        if (event.key === "ArrowLeft") {{
            if (currentIndex > 0) {{
                currentIndex--;
                updateCard();
            }}
        }} else if (event.key === "ArrowRight") {{
            if (currentIndex < cards.length - 1) {{
                currentIndex++; 
                updateCard();
            }}
        }} else if (event.key === "Enter") {{
            card.classList.toggle("flipped");
        }}
    }});
    document.addEventListener("DOMContentLoaded", () => {{
        const homeBtn = document.querySelector(".home-btn");
        homeBtn.addEventListener("click", goHome);
    }});
</script>
</body>
</html>
"""    

    # Stub
    pass
