from flask import render_template, request, redirect, send_file, jsonify, url_for
import os, json, shutil
from pathlib import Path
from .utils import (
    sanitize_filename,
    generate_flashcard_html,
    load_sets_with_counts,
    load_sets_for_mode,
    handle_flashcard_creation,
    load_set_modes,
    save_set_modes,
    get_all_sets,
    get_azure_token,
)
from .git_utils import commit_and_push_changes, delete_set_and_push

def init_routes(app):

    # === Public Home ===
    @app.route("/")
    def landing_page():
        return render_template("index.html")

    # === Learning Mode Pages ===
    @app.route("/flashcards")
    def flashcards_home():
        sets = load_sets_for_mode("flashcard")
        return render_template("flashcards_home.html", sets=sets)

    @app.route("/practice")
    def practice_home():
        sets = load_sets_for_mode("practice")
        return render_template("practice_home.html", sets=sets)

    @app.route("/reading")
    def reading_home():
        sets = load_sets_for_mode("reading")
        return render_template("reading_home.html", sets=sets)

    @app.route("/listening")
    def listening_home():
        sets = load_sets_for_mode("listening")
        return render_template("listening_home.html", sets=sets)

    @app.route("/test")
    def test_home():
        sets = load_sets_for_mode("test")
        return render_template("test_home.html", sets=sets)

    # === Azure Token Endpoint ===
    @app.route("/api/token", methods=["GET"])
    def get_token():
        return get_azure_token()

    # === Static/Output File Serving ===
    @app.route("/custom_static/<path:filename>")
    def serve_static_file(filename):
        project_root = Path(__file__).resolve().parent.parent
        full_path = project_root / "docs" / "static" / Path(filename)
        if not full_path.exists():
            print("❌ Audio file not found:", full_path)
            return "Audio file not found", 404
        return send_file(full_path)

    @app.route("/output/<path:filename>")
    def serve_output_file(filename):
        project_root = Path(__file__).resolve().parent.parent
        full_path = project_root / "docs" / "output" / Path(filename)
        if not full_path.exists():
            print("❌ File not found:", full_path)
            return "File not found", 404
        return send_file(full_path)

    @app.route("/docs")
    def serve_docs_home():
        docs_index = Path(__file__).resolve().parent.parent / "docs" / "index.html"
        if not docs_index.exists():
            return "Homepage not found", 404
        return send_file(docs_index)

    # === Set Management System ===
    @app.route("/manage_sets", methods=["GET"])
    def manage_sets():
        sets = get_all_sets()
        set_modes = load_set_modes()
        modes = ["flashcard", "practice", "reading"]
        return render_template("manage_sets.html", sets=sets, set_modes=set_modes, modes=modes)
   
    @app.route("/create", methods=["GET", "POST"])
    def create_set_page():
        if request.method == "POST":
            return handle_flashcard_creation(request.form)

        set_name = request.args.get("set_name", "")
        return render_template("create.html", set_name=set_name)
    
    @app.route("/create_set", methods=["POST"])
    def create_set_with_data():
        name = request.form.get("new_set_name", "").strip()
        if name:
            set_dir = os.path.join("docs/sets", name)
            os.makedirs(set_dir, exist_ok=True)

            json_path = os.path.join(set_dir, "data.json")
            if not os.path.exists(json_path):
                with open(json_path, "w") as f:
                    f.write("[]")  # start with empty list

            print(f"✅ Created set: {name}")
            return redirect(url_for("create_set_page", set_name=name))

        return redirect(url_for("manage_sets"))

    @app.route("/delete_set", methods=["POST"])
    def delete_set():
        name = request.form.get("delete_set_name")
        if name:
            shutil.rmtree(os.path.join("docs/sets", name), ignore_errors=True)
            print(f"🗑️ Deleted set: {name}")
        return redirect(url_for("manage_sets"))

    @app.route("/update_set_config", methods=["POST"])
    def update_set_config():
        data = request.form.to_dict(flat=False)
        sets = get_all_sets()
        config = {}
        for set_name in sets:
            config[set_name] = data.get(set_name, [])
        save_set_modes(config)
        print(f"💾 Updated mode config: {config}")
        return redirect(url_for("manage_sets"))
