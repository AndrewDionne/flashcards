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
    SETS_DIR
)
from .git_utils import commit_and_push_changes, delete_set_and_push

def init_routes(app):

    # === Public Home ===
    @app.route("/")
    def home():
        sets = get_all_sets()  # or however you load set names
        set_modes = load_set_modes()  # your config loader
        return render_template("index.html", sets=sets, set_modes=set_modes)

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
        set_dirs = [d for d in SETS_DIR.iterdir() if d.is_dir()]
        sets = []
        for d in set_dirs:
            with open(d / "data.json", encoding="utf-8") as f:
                data = json.load(f)

            modes_dict = {
                "flashcards": Path(f"docs/output/{d.name}/flashcards.html").exists(),
                "practice": Path(f"docs/output/{d.name}/practice.html").exists(),
                "reading": Path(f"docs/output/{d.name}/reading.html").exists(),
                "listening": Path(f"docs/output/{d.name}/listening.html").exists(),
                "test": Path(f"docs/output/{d.name}/test.html").exists(),
            }
            available_modes = [m for m, active in modes_dict.items() if active]

            sets.append({
                "name": d.name,
                "count": len(data),
                "modes": available_modes
            })

        return render_template("manage_sets.html", sets_data=sets)

    @app.route("/update_set_modes", methods=["POST"])
    def update_set_modes():
        # Read the submitted checkboxes
        updated_modes = {}
        for set_dir in SETS_DIR.iterdir():
            if set_dir.is_dir():
                selected_modes = []
                for mode in ["flashcards", "practice", "reading", "listening", "test"]:
                    if f"{set_dir.name}_{mode}" in request.form:
                        selected_modes.append(mode)
                updated_modes[set_dir.name] = selected_modes
                # TODO: Save modes to a config file for this set

        # Save per-set mode config (example: modes.json inside each set folder)
        for set_name, modes in updated_modes.items():
            modes_file = SETS_DIR / set_name / "modes.json"
            with open(modes_file, "w", encoding="utf-8") as f:
                json.dump(modes, f, ensure_ascii=False, indent=2)

        flash("Modes updated successfully!", "success")
        return redirect(url_for("manage_sets"))
    
    @app.route("/delete_sets", methods=["GET", "POST"])
    def delete_sets():
        if request.method == "POST":
            for set_name in request.form.getlist("sets_to_delete"):
                shutil.rmtree(SETS_DIR / set_name, ignore_errors=True)
            flash("Selected sets deleted successfully!", "success")
            return redirect(url_for("manage_sets"))

        all_sets = [d.name for d in SETS_DIR.iterdir() if d.is_dir()]
        return render_template("delete_sets.html", all_sets=all_sets)

   
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
