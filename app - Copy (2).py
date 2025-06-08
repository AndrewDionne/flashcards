from flask import Flask, render_template, request, redirect, send_from_directory
import os
import json
from gtts import gTTS

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            set_name = request.form["set_name"].strip()
            json_input = request.form["json_input"].strip()
            data = json.loads(json_input)
        except Exception as e:
            return f"<h2 style='color:red;'>❌ Error: {str(e)}</h2>", 400

        # Create output directories
        audio_dir = os.path.join("static", set_name, "audio")
        output_dir = os.path.join("output", set_name)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Generate audio and HTML for each card
        card_html = ""
        for i, entry in enumerate(data):
            phrase = entry["phrase"]
            pronunciation = entry["pronunciation"]
            meaning = entry["meaning"]

            filename = f"{i}_{phrase}.mp3".replace(" ", "_")
            filepath = os.path.join(audio_dir, filename)
            tts = gTTS(text=phrase, lang="pl")
            tts.save(filepath)

            card_html += f"""
            <div class="card">
                <div class="front">{meaning}</div>
                <div class="back">
                    <p>{phrase}</p>
                    <p><em>{pronunciation}</em></p>
                    <audio controls>
                        <source src="/static/{set_name}/audio/{filename}" type="audio/mpeg">
                    </audio>
                </div>
            </div>
            """

        # Wrap cards in basic HTML layout
        full_html = f"""
 <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{set_name} Flashcards</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                h1 {{
                    font-size: 1.5em;
                    margin-bottom: 20px;
                }}
                .card {{
                    width: 90vw;
                    max-width: 350px;
                    height: 220px;
                    perspective: 1000px;
                    margin-bottom: 20px;
                }}
                .card-inner {{
                    width: 100%;
                    height: 100%;
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
                    width: 100%;
                    height: 100%;
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
                const cardInner = document.getElementById("cardInner");
                const prevBtn = document.getElementById("prevBtn");
                const nextBtn = document.getElementById("nextBtn");

                function updateCard() {{
                    const entry = cards[currentIndex];
                    const filename = `${{currentIndex}}_${{entry.phrase}}.mp3`.replace(/\\s+/g, "_");
                    cardFront.innerHTML = entry.meaning;
                    cardBack.innerHTML = `
                        <p>${{entry.phrase}}</p>
                        <p><em>${{entry.pronunciation}}</em></p>
                        <audio controls>
                            <source src="/static/{set_name}/audio/${{filename}}" type="audio/mpeg">
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

        # Save the HTML file
        output_html_path = os.path.join(output_dir, "flashcards.html")
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        # Redirect to the generated flashcards
        return redirect(f"/output/{set_name}/flashcards.html")

    return render_template("index.html")


# Serve generated HTML from the output folder
@app.route("/output/<path:filename>")
def serve_output_file(filename):
    return send_from_directory("output", filename)


if __name__ == "__main__":
    print("\n🚀 Starting Flask app...")
    app.run(debug=True)
