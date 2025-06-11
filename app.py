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

# Serve audio files from the 'audio' folder
@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory('audio', filename)

def sanitize_filename(text):
    # Replace all non-alphanumeric chars with underscore for safe filenames
    return re.sub(r'[^a-zA-Z0-9]', '_', text)
#this is the code for generating the flash cards
# This is the code for generating the flash cards
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
        except Exception as e:
            return f"<h2 style='color:red;'>❌ Error: {str(e)}</h2>", 400

        # Create output dirs
        audio_dir = os.path.join("static", set_name, "audio")
        output_dir = os.path.join("output", set_name)
        sets_dir = os.path.join("sets", set_name)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(sets_dir, exist_ok=True)

        # Generate audio
        for i, entry in enumerate(data):
            phrase = entry["phrase"]
            filename = f"{i}_{sanitize_filename(phrase)}.mp3"
            filepath = os.path.join(audio_dir, filename)
            if not os.path.exists(filepath):
                tts = gTTS(text=phrase, lang="pl")
                tts.save(filepath)

        # Write JSON file for consistency / export
        with open(os.path.join(sets_dir, "data.json"), "w", encoding="utf-8") as json_out:
            json.dump(data, json_out, ensure_ascii=False, indent=2)

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
            margin-bottom: 20px;
            margin-left: 10px;
            display: flex;
            justify-content: center;
            align-items: center;
            box-sizing: border-box;
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
            word-wrap: break-word;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .card-back {{
            background: #e9ecef;
            transform: rotateY(180deg);
            flex-direction: column;
            font-size: 1.1em;
            text-align: center;
            word-wrap: break-word;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .card-back button {{
            margin-top: 10px;
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
            gap: 15px;
            margin-top: 30px;
            justify-content: center;
        }}
        button {{
            padding: 10px 20px;
            font-size: 1em;
            border: none;
            border-radius: 8px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
            flex: 1;
        }}
        button:disabled {{
            background-color: #aaa;
            cursor: default;
        }}
    </style>
</head>
<body>
    <h1>
    {set_name} Flashcards
        <button class="home-btn" onclick="window.location.href='/'">🏠</button>
    </h1>
    <div class="card" id="cardContainer">
        <div class="card-inner" id="cardInner">
            <div class="card-front" id="cardFront"></div>
            <div class="card-back" id="cardBack"></div>
        </div>
    </div>
    <div class="nav-buttons">
        <button id="prevBtn">Previous</button>
        <button id="nextBtn">Next</button>
    
    <audio id="audioPlayer" preload="auto">
        <source id="audioSource" src="" type="audio/mpeg" />
        Your browser does not support the audio element.
    </audio>
"""
        # JavaScript part (add after HTML body layout)
        html_script = f"""
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
            <button onclick="playAudio('${{filename}}')">▶️ Play Audio</button>
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
            // Go to the root of the repo on GitHub Pages or localhost
            if (window.location.hostname === "andrewdionne.github.io") {{
                const repo = window.location.pathname.split("/")[1]; // e.g., WSPOL-Names
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
</script>
</body>
</html>
"""

        # Write to output
        output_html_path = os.path.join(output_dir, "flashcards.html")
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(full_html + html_script)

        return redirect(f"/output/{set_name}/flashcards.html")

    return render_template("index.html")




# Serve generated HTML and static files
@app.route("/")
def homepage():
    output_root = "output"
    static_root = "static"
    sets_dict = {}

    # Step 1: Collect sets from output/
    if os.path.exists(output_root):
        for set_name in sorted(os.listdir(output_root)):
            set_dir = os.path.join(output_root, set_name)
            if os.path.isdir(set_dir):
                sets_dict[set_name] = {"name": set_name, "count": "?"}

    # Step 2: Count audio files from static/
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
                    sets_dict[set_name]["count"] = card_count  # update count if known

    sets = list(sets_dict.values())
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

# TO DELETE 
@app.route('/delete_set/<set_name>', methods=['POST'])
def delete_set(set_name):
    import time
    repo_path = os.path.abspath(os.path.dirname(__file__))  # More robust than hardcoding

# Paths to delete
    paths_to_delete = [
        os.path.join(repo_path, "output", set_name),
        os.path.join(repo_path, "static", set_name),
        os.path.join(repo_path, "sets", set_name)
    ]

    deleted_anything = False

    for path in paths_to_delete:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Deleted: {path}")
            deleted_anything = True
        else:
            print(f"Not found (skipped): {path}")

    if deleted_anything:
        # Git commit + push
        repo = Repo(repo_path)
        repo.git.add(update=True)
        repo.index.commit(f"Deleted flashcard set: {set_name}")
        origin = repo.remote(name='origin')
        origin.push()
        print(f"Pushed deletion of {set_name} to GitHub.")
        time.sleep(2)

    return redirect(url_for('homepage'))




def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    print("\n🚀 Starting Flask app...")
    app.run(debug=True)