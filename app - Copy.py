from flask import Flask, render_template, request, redirect, send_from_directory, url_for
import os
import json
from gtts import gTTS
import re
from git import Repo
import webbrowser
import threading
import shutil

app = Flask(__name__)

def sanitize_filename(text):
    # Replace all non-alphanumeric chars with underscore for safe filenames
    return re.sub(r'[^a-zA-Z0-9]', '_', text)
#this is the code for generating the flash cards
@app.route("/create", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            set_name = request.form["set_name"].strip()
            json_input = request.form["json_input"].strip()
            data = json.loads(json_input)

            # Validate keys
            for entry in data:
                if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
                    raise ValueError("Each entry must have 'phrase', 'pronunciation', and 'meaning' keys.")

            # Convert the data list to JSON string for embedding in JS
            cards_json = json.dumps(data, ensure_ascii=False)

            # Prepare directories for audio and output
            audio_dir = os.path.join("static", set_name, "audio")
            output_dir = os.path.join("output", set_name)
            os.makedirs(audio_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            # Generate audio files for each phrase if not already present
            for i, entry in enumerate(data):
                phrase = entry["phrase"]
                filename = f"{i}_{sanitize_filename(phrase)}.mp3"
                filepath = os.path.join(audio_dir, filename)
                if not os.path.exists(filepath):
                    tts = gTTS(text=phrase, lang="pl")
                    tts.save(filepath)

            # Now build the HTML page string with cards_json embedded
            full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Flashcards</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
        /* Your CSS here */
    </style>
</head>
<body>
    <h1>Polish Flashcards</h1>
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

    <audio id="audioPlayer" preload="auto">
        <source id="audioSource" src="" type="audio/mpeg" />
        Your browser does not support the audio element.
    </audio>

    <script>
        const cards = {cards_json};

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
                <button onclick="playAudio('${{filename}}')">▶️ Play Audio</button>
            `;
            prevBtn.disabled = currentIndex === 0;
            nextBtn.disabled = currentIndex === cards.length - 1;
            card.classList.remove("flipped");
        }}

        function playAudio(filename) {{
            const audio = document.getElementById("audioPlayer");
            const source = document.getElementById("audioSource");
            const newSrc = `./audio/${{filename}}`;
            if (source.src !== location.href + newSrc) {{
                source.src = newSrc;
                audio.load();
            }}
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
    </script>
</body>
</html>
"""

            # Write the HTML file
            output_html_path = os.path.join(output_dir, "flashcards.html")
            with open(output_html_path, "w", encoding="utf-8") as f:
                f.write(full_html)

            return redirect(f"/output/{set_name}/flashcards.html")

        except Exception as e:
            return f"<h2 style='color:red;'>❌ Error: {str(e)}</h2>", 400

    # For GET requests, just render the input form page
    return render_template("index.html")


# Serve generated HTML and static files
@app.route("/")
def homepage():
    output_root = "output"
    sets = []

    if os.path.exists(output_root):
        for set_name in sorted(os.listdir(output_root)):
            set_dir = os.path.join(output_root, set_name)
            data_file = os.path.join(set_dir, "flashcards.html")
            if os.path.isdir(set_dir) and os.path.exists(data_file):
                try:
                    # Estimate number of cards by counting audio files
                    audio_path = os.path.join("static", set_name, "audio")
                    card_count = len([
                        f for f in os.listdir(audio_path)
                        if f.endswith(".mp3")
                    ]) if os.path.exists(audio_path) else 0
                    sets.append({"name": set_name, "count": card_count})
                except Exception:
                    sets.append({"name": set_name, "count": "?"})  # fallback

    return render_template("homepage.html", sets=sets)

@app.route("/output/<path:filename>")
def serve_output_file(filename):
    return send_from_directory("output", filename)

@app.route("/publish", methods=["GET", "POST"])
def publish():
    if request.method == "POST":
        try:
            # 1. Create "docs" folder structure for GitHub Pages
            if not os.path.exists("docs"):
                os.makedirs("docs/sets")

            sets = sorted([
                d for d in os.listdir("output")
                if os.path.isdir(os.path.join("output", d))
                and os.path.exists(os.path.join("output", d, "flashcards.html"))
            ])

            # 2. Copy HTML and audio files
            for set_name in sets:
                dst_set_dir = os.path.join("docs", "sets", set_name)
                os.makedirs(dst_set_dir, exist_ok=True)
                src_html = os.path.join("output", set_name, "flashcards.html")
                dst_html = os.path.join(dst_set_dir, "flashcards.html")
                shutil.copyfile(src_html, dst_html)

                src_audio = os.path.join("static", set_name, "audio")
                dst_audio = os.path.join("docs", "sets", set_name, "audio")
                if os.path.exists(src_audio):
                    shutil.copytree(src_audio, dst_audio, dirs_exist_ok=True)

            homepage_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Flashcard Sets</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {{
      font-family: 'Inter', sans-serif;
      background: #f1f3f8;
      margin: 0;
      padding: 30px 20px;
      color: #333;
    }}
    h1 {{
      font-size: 2rem;
      text-align: center;
      margin-bottom: 40px;
      color: #1a202c;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 24px;
      max-width: 1000px;
      margin: 0 auto;
    }}
    .set-card {{
      background: #ffffff;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      text-align: center;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .set-card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }}
    .set-card a {{
      text-decoration: none;
      color: #2563eb;
      font-size: 1.1rem;
      font-weight: 600;
      display: block;
    }}
    .set-card a:hover {{
      text-decoration: underline;
    }}
    @media (hover: none) {{
      .set-card:hover {{
        transform: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      }}
    }}
  </style>
</head>
<body>
  <h1>📚 Choose a Polish Flashcard Set</h1>
  <div class="card-grid">
"""

            for set_name in sets:
                homepage_html += f"""
    <div class="set-card">
      <a href="sets/{set_name}/flashcards.html">{set_name}</a>
    </div>
    """

            homepage_html += """
  </div>
</body>
</html>
"""

            with open(os.path.join("docs", "index.html"), "w", encoding="utf-8") as f:
                f.write(homepage_html)

            # 4. Commit and push
            repo = Repo(os.getcwd())
            repo.git.add(A=True)
            repo.index.commit("📘 Publish flashcard sets with homepage")
            repo.remote(name="origin").push()

            return f"<h3 style='color:green;'>✅ All flashcard sets published to GitHub Pages.</h3><a href='/'>⬅ Back to homepage</a>"
        except Exception as e:
            return f"<h3 style='color:red;'>❌ Git publish failed: {e}</h3><a href='/'>⬅ Back to homepage</a>"
    else:
        return render_template("publish.html", sets=sorted(os.listdir("output")))

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    print("\n🚀 Starting Flask app...")
    app.run(debug=True)