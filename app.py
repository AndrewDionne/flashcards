from flask import Flask, render_template, request, redirect, send_from_directory, url_for
import os
import json
from gtts import gTTS
import re
from git import Repo
import webbrowser
import threading

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

            # Validate data keys in each entry
            for entry in data:
                if not all(k in entry for k in ("phrase", "pronunciation", "meaning")):
                    raise ValueError("Each entry must have 'phrase', 'pronunciation', and 'meaning' keys.")
        except Exception as e:
            return f"<h2 style='color:red;'>❌ Error: {str(e)}</h2>", 400

        # Create output directories
        audio_dir = os.path.join("static", set_name, "audio")
        output_dir = os.path.join("output", set_name)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Generate audio files
        for i, entry in enumerate(data):
            phrase = entry["phrase"]
            filename = f"{i}_{sanitize_filename(phrase)}.mp3"
            filepath = os.path.join(audio_dir, filename)
            if not os.path.exists(filepath):  # Avoid re-generating if exists
                tts = gTTS(text=phrase, lang="pl")
                tts.save(filepath)

        # Prepare flashcards page HTML with next/prev and flip card
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
        }}
        h1 {{
            font-size: 1.5em; margin-bottom: 20px;
        }}
        .card {{
            width: 90vw; max-width: 350px; height: 220px;
            perspective: 1000px; margin-bottom: 20px;
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
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 1.4em;
            padding: 20px;
            backface-visibility: hidden;
        }}
        .card-front {{
            background: #ffffff;
            font-weight: bold;
            text-align: center;
        }}
        .card-back {{
            background: #e9ecef;
            transform: rotateY(180deg);
            flex-direction: column;
            font-size: 1.1em;
            text-align: center;
        }}
        .card-back audio {{
            margin-top: 10px;
            width: 100%;
        }}
        .nav-buttons {{
            display: flex;
            gap: 15px;
        }}
        button {{
            padding: 10px 20px;
            font-size: 1em;
            border: none;
            border-radius: 8px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
        }}
        button:disabled {{
            background-color: #aaa;
            cursor: default;
        }}
    </style>
</head>
<body>
    <h1>{set_name} Flashcards</h1>
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

    <script>
        const cards = {json.dumps(data)};
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
                <audio controls>
                    <source src="/static/{set_name}/audio/${{filename}}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
            `;
            prevBtn.disabled = currentIndex === 0;
            nextBtn.disabled = currentIndex === cards.length - 1;
            card.classList.remove("flipped");
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

        card.addEventListener("click", () => {{
            card.classList.toggle("flipped");
        }});

        updateCard();
    </script>
</body>
</html>
"""

        # Save generated flashcards HTML
        output_html_path = os.path.join(output_dir, "flashcards.html")
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        # Redirect to flashcards page
        return redirect(f"/output/{set_name}/flashcards.html")

    # GET method: render the form to input flashcard set name + JSON data
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
        set_name = request.form["set_name"]
        commit_message = request.form.get("commit_message", f"Add flashcard set {set_name}")
        repo_path = os.getcwd()  # Your Git repo path
        output_path = os.path.join("output", set_name)

        try:
            repo = Repo(repo_path)
            repo.git.add(A=True)
            repo.index.commit(commit_message)
            origin = repo.remote(name="origin")
            origin.push()
            return f"<h3 style='color:green;'>✅ Successfully pushed '{set_name}' to GitHub.</h3><a href='/'>⬅ Back to homepage</a>"
        except Exception as e:
            return f"<h3 style='color:red;'>❌ Git push failed: {e}</h3><a href='/'>⬅ Back to homepage</a>"
    else:
        # For GET: populate dropdown with available sets
        sets = sorted([
            d for d in os.listdir("output")
            if os.path.isdir(os.path.join("output", d))
            and os.path.exists(os.path.join("output", d, "flashcards.html"))
        ])
        return render_template("publish.html", sets=sets)

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    print("\n🚀 Starting Flask app...")
    app.run(debug=True)