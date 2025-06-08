from flask import Flask, render_template, request, send_file
from gtts import gTTS
import os, shutil, json
from zipfile import ZipFile

app = Flask(__name__)
OUTPUT_DIR = "output"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = json.loads(request.form['jsonInput'])

        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(AUDIO_DIR)

        # Generate audio
        for entry in data:
            phrase = entry["phrase"]
            filename = phrase.replace(" ", "_").replace(",", "").replace("–", "-") + ".mp3"
            tts = gTTS(text=phrase, lang='pl')
            tts.save(os.path.join(AUDIO_DIR, filename))

        # Generate HTML
        html = generate_html(data)
        with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

        # Zip files
        zip_path = "flashcards.zip"
        with ZipFile(zip_path, "w") as zipf:
            for folder, _, files in os.walk(OUTPUT_DIR):
                for file in files:
                    path = os.path.join(folder, file)
                    arc = os.path.relpath(path, OUTPUT_DIR)
                    zipf.write(path, arc)

        return send_file(zip_path, as_attachment=True)

    except Exception as e:
        return f"Error: {str(e)}", 500

def generate_html(data):
    cards_js_array = json.dumps(data, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Polish Phrase Flashcards</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
      background-color: #f4f4f4;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }}
    .card {{
      width: 90vw;
      max-width: 340px;
      height: 220px;
      perspective: 1000px;
      margin-bottom: 20px;
    }}
    .card-inner {{
      position: relative;
      width: 100%;
      height: 100%;
      transition: transform 0.6s;
      transform-style: preserve-3d;
    }}
    .card.flipped .card-inner {{
      transform: rotateY(180deg);
    }}
    .card-front, .card-back {{
      position: absolute;
      width: 100%;
      height: 100%;
      background: white;
      border-radius: 16px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 20px;
      box-sizing: border-box;
      backface-visibility: hidden;
      text-align: center;
    }}
    .card-back {{
      transform: rotateY(180deg);
      flex-direction: column;
    }}
    .navigation {{
      display: flex;
      gap: 10px;
    }}
    button {{
      padding: 10px 16px;
      font-size: 1rem;
      border: none;
      border-radius: 8px;
      background-color: #007bff;
      color: white;
      cursor: pointer;
    }}
    .pronunciation {{
      font-size: 1rem;
      margin: 10px 0;
    }}
  </style>
</head>
<body>

  <div class="card" id="flashcard" onclick="flipCard()">
    <div class="card-inner">
      <div class="card-front" id="card-front"></div>
      <div class="card-back" id="card-back"></div>
    </div>
  </div>

  <div class="navigation">
    <button onclick="prevCard()">Previous</button>
    <button onclick="nextCard()">Next</button>
  </div>

  <script>
    const flashcards = {cards_js_array};
    let currentIndex = 0;
    const card = document.getElementById('flashcard');
    const front = document.getElementById('card-front');
    const back = document.getElementById('card-back');

    function renderCard() {{
      const entry = flashcards[currentIndex];
      const fileName = entry.phrase.replace(/\\s|,|–/g, '_');
      front.textContent = entry.meaning;
      back.innerHTML = `
        <div><strong>${{entry.phrase}}</strong></div>
        <div class="pronunciation">${{entry.pronunciation}}</div>
        <button onclick="event.stopPropagation(); playAudio('${{fileName}}')">🔊 Play</button>
      `;
    }}

    function flipCard() {{
      card.classList.toggle('flipped');
    }}

    function nextCard() {{
      if (currentIndex < flashcards.length - 1) currentIndex++;
      card.classList.remove('flipped');
      renderCard();
    }}

    function prevCard() {{
      if (currentIndex > 0) currentIndex--;
      card.classList.remove('flipped');
      renderCard();
    }}

    function playAudio(name) {{
      const audio = new Audio('audio/' + name + '.mp3');
      audio.play().catch(e => console.error('Audio error:', e));
    }}

    renderCard();
  </script>
</body>
</html>"""
