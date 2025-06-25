from flask import render_template, request, redirect, send_from_directory, jsonify, url_for
import os, json, shutil
from .utils import sanitize_filename, generate_flashcard_html, load_sets_with_counts, handle_flashcard_creation
from .git_utils import commit_and_push_changes, delete_set_and_push
from flask import send_file
from pathlib import Path

def init_routes(app):

    @app.route("/")
    def homepage():
        sets = load_sets_with_counts()
        return render_template("homepage.html", sets=sets)

    @app.route("/create", methods=["GET", "POST"])
    def create():
        if request.method == "POST":
            return handle_flashcard_creation(request.form)
        return render_template("index.html")

    @app.route("/api/token", methods=["GET"])
    def get_token():
        from .utils import get_azure_token
        return get_azure_token()

    @app.route("/custom_static/<path:filename>")
    def serve_static_file(filename):
        print("Raw audio request path:", filename)

        project_root = Path(__file__).resolve().parent.parent
        full_path = project_root / "docs" / "static" / Path(filename)

        print("🎧 Full resolved static path:", full_path)

        if not full_path.exists():
            print("❌ Audio file not found:", full_path)
            return "Audio file not found", 404

        return send_file(full_path)

    @app.route("/docs")
    def serve_docs_home():
        docs_index = Path(__file__).resolve().parent.parent / "docs" / "index.html"
        if not docs_index.exists():
            return "Homepage not found", 404
        return send_file(docs_index)
    
    #@app.route("/audio/<filename>")
    #def serve_audio(filename):
        #return send_from_directory("audio", filename)

    @app.route("/output/<path:filename>")
    def serve_output_file(filename):
        print("Raw filename from browser:", filename)

        # Resolve based on the project root, not the current file's folder
        project_root = Path(__file__).resolve().parent.parent
        full_path = project_root / "docs" / "output" / Path(filename)

        print("📄 Normalized full path:", full_path)

        if not full_path.exists():
            print("❌ File not found:", full_path)
            return "File not found", 404

        return send_file(full_path)
    @app.route("/practice/<set_name>")
    def serve_practice_page(set_name):
        practice_path = Path(__file__).resolve().parent.parent / "docs" / "output" / set_name / "practice.html"
        if not practice_path.exists():
            return "Practice page not found", 404
        return send_file(practice_path)

    #@app.route("/output/<path:filename>")
    #def serve_output_file(filename):
        #return send_from_directory("output", filename)

    @app.route("/delete_set/<set_name>", methods=["POST"])
    def delete_set(set_name):
        delete_set_and_push(set_name)
        update_docs_homepage()  # ✅ add this line
        return redirect(url_for('homepage'))

    @app.route("/delete_sets", methods=["POST"])
    def delete_sets():
        data = request.get_json()
        sets_to_delete = data.get('sets', [])
        if not sets_to_delete:
            return jsonify(success=False, message="No sets specified."), 400

        for set_name in sets_to_delete:
            delete_set_and_push(set_name)

        return jsonify(success=True)
