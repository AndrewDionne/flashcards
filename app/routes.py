from flask import render_template, request, redirect, send_from_directory, jsonify, url_for
import os, json, shutil
from .utils import sanitize_filename, generate_flashcard_html, load_sets_with_counts, handle_flashcard_creation
from .git_utils import commit_and_push_changes, delete_set_and_push

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

    @app.route("/audio/<filename>")
    def serve_audio(filename):
        return send_from_directory("audio", filename)

    @app.route("/output/<path:filename>")
    def serve_output_file(filename):
        # Normalize path to fix Windows backslash issue
        normalized_filename = filename.replace("\\", "/")
        full_path = os.path.join("output", normalized_filename)
        print("📄 Trying to serve:", full_path)
        if not os.path.exists(full_path):
            print("❌ File not found:", full_path)
        return send_from_directory("output", normalized_filename)

    #@app.route("/output/<path:filename>")
    #def serve_output_file(filename):
        #return send_from_directory("output", filename)

    @app.route("/delete_set/<set_name>", methods=["POST"])
    def delete_set(set_name):
        delete_set_and_push(set_name)
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
