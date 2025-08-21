import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
import db_connection
from demucs_splitter import separate_vocals, separate_drums, separate_bass, separate_other
from ensemble import ensemble_eq
from genre_identify import find_genre

user_blueprint = Blueprint('user_actions', __name__)
connection = db_connection.get_db_conn()

UPLOAD_FOLDER = "static/audios/original"
RENDERED_FOLDER = "static/audios/rendered/"
ALLOWED_EXTENSIONS = {"wav"}
# Ensure the folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@user_blueprint.route('/home')
def index():
    if session.get('logged_in'):
        connection.reconnect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''SELECT * FROM renderings WHERE u_id = %s AND status = 1''', (session['u_id'],))
        songs = cursor.fetchall()
        return render_template('user/index.html', songs=songs, current_route=request.endpoint)
    else:
        return redirect(url_for('login_out.login_page'))


@user_blueprint.route('/splitter')
def splitter():
    if session.get('logged_in'):
        return render_template('user/splitter.html', song_data=None, current_route=request.endpoint)
    else:
        return redirect(url_for('login_out.login_page'))


@user_blueprint.route('/split', methods=['POST'])
def split():
    if "audio" not in request.files:
        print("No audio")
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["audio"]
    audio_type = request.form.get('audio-type')
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save the file temporarily
    filename = secure_filename(file.filename)
    filename_wo_ext = os.path.splitext(os.path.basename(filename))[0]
    temp_filepath = os.path.join('E:\Main Project\FlaskEq\static\\audios\splitter_input', filename)
    output_path = 'E:\Main Project\FlaskEq\static\\audios\splitter_output'
    file.save(temp_filepath)
    extracted_file = ''
    if audio_type == "Vocals":
        separate_vocals(temp_filepath, output_path)
        extracted_file = (filename_wo_ext + '_vocals.wav')
    elif audio_type == "Drums":
        separate_drums(temp_filepath, output_path)
        extracted_file = (filename_wo_ext + '_drums.wav')
    elif audio_type == "Bass":
        separate_bass(temp_filepath, output_path)
        extracted_file = (filename_wo_ext + '_bass.wav')
    elif audio_type == "Others":
        separate_other(temp_filepath, output_path)
        extracted_file = (filename_wo_ext + '_other.wav')

    file_size_bytes = os.path.getsize(output_path + '\\' + extracted_file)
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    return jsonify(
        {"message": "Audio generated successfully", 'audio_type': audio_type, 'file_size_mb': f'{file_size_mb:.2f} MB',
         'extracted_url': url_for('static', filename=f'audios/splitter_output/{extracted_file}')}), 200


@user_blueprint.route('/studio')
def studio():
    if not session.get('logged_in'):
        return redirect(url_for('login_out.login_page'))

    music_id = request.args.get('music_id')  # Get music_id from query parameters

    song_data = None
    if music_id:
        connection.reconnect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''SELECT r.music_id, r.title, r.artist, r.original, r.rendered, r.genre_id, g.genre
            FROM renderings r JOIN genres g ON r.genre_id = g.genre_id  WHERE r.music_id = %s ''', (music_id,))
        song_data = cursor.fetchone()  # Get the row
        file_size_bytes = os.path.getsize(
            'E:\Main Project\FlaskEq\static\\audios\\rendered' + '\\' + song_data['rendered'])
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
        song_data['file_size_mb'] = f'{file_size_mb:.2f} MB'
    return render_template('user/studio.html', username=session['username'],
                           profile_pic=session['profile_pic'], song_data=song_data, current_route=request.endpoint)


@user_blueprint.route('/upload_wav', methods=['POST'])
def upload_wav():
    if not session.get('logged_in'):
        return redirect(url_for('login_out.login_page'))

    if "audio" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["audio"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Retrieve song title and artist name from form data
    title = request.form.get("songTitle")
    artist = request.form.get("artistName")

    if not title or not artist:
        return jsonify({"error": "Song title and artist name are required"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format"}), 400

    connection.reconnect()
    cursor = connection.cursor(dictionary=True)

    # Get genres from database
    cursor.execute("SELECT * FROM genres")
    genre_mapping = cursor.fetchall()

    # Convert result to a dictionary: {genre_id - 1: genre}
    genre_dict = {item['genre_id'] - 1: item['genre'] for item in genre_mapping}

    # Save the file temporarily
    filename = secure_filename(file.filename)
    temp_filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_filepath)

    # Identify genre
    identified_genre = find_genre(temp_filepath, genre_dict)
    if identified_genre == 'error':
        return jsonify({"error": identified_genre}), 400

    try:
        # Insert into the database (without file name initially)
        cursor.execute(
            "INSERT INTO renderings (u_id, title, artist, genre_id, original) VALUES (%s, %s, %s, %s, '')",
            (session['u_id'], title, artist, identified_genre['genre_id'])
        )
        connection.commit()

        inserted_music_id = cursor.lastrowid  # Get the last inserted ID

        # Generate new filename with music_id
        file_name_w_music_id = f"{inserted_music_id}_{filename}"
        final_filepath = os.path.join(UPLOAD_FOLDER, file_name_w_music_id)

        # Rename the temporary file
        os.rename(temp_filepath, final_filepath)

        # Update the database with the correct file name
        cursor.execute("UPDATE renderings SET original = %s WHERE music_id = %s",
                       (file_name_w_music_id, inserted_music_id))
        connection.commit()

        return jsonify({
            "message": "File uploaded successfully",
            "genre": identified_genre['genre'],
            "genre-id": identified_genre['genre_id'],
            "music-id": inserted_music_id
        }), 200

    except Exception as e:
        connection.rollback()  # Rollback in case of error
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    finally:
        cursor.close()


@user_blueprint.route('/generate_audio', methods=['GET', 'POST'])
def generate_audio():
    if session.get('logged_in'):
        try:
            data = request.get_json()  # Parse the incoming JSON data
            music_id = data.get('music_id')
            genre_id = data.get('genre_id')

            connection.reconnect()
            cursor = connection.cursor(dictionary=True)
            cursor.execute('''SELECT original FROM renderings WHERE music_id = %s''', (music_id,))
            result_data = cursor.fetchone()
            cursor.close()

            if not result_data:
                return jsonify({"error": "Music ID not found"}), 404

            file_name = result_data['original']
            new_file_name = "EQ_" + file_name
            source_audio_path = os.path.join(UPLOAD_FOLDER, file_name)

            # ---------- RENDERING AUDIO ------------ #
            result = ensemble_eq(source_audio_path, int(genre_id), os.path.join(RENDERED_FOLDER, new_file_name))
            # ---------- RENDERING AUDIO ------------ #

            if result:
                # INSERT INTO DB
                connection.reconnect()
                cursor = connection.cursor(dictionary=True)
                cursor.execute("UPDATE renderings SET rendered = %s WHERE music_id = %s", (new_file_name, music_id))
                connection.commit()
                cursor.close()
                print("Updated Database")
                return jsonify({"message": "Audio generated successfully", "rendered_file_name": new_file_name}), 200
            else:
                return jsonify({"error": "Error generating audio"}), 400

        except Exception as e:
            print(f"Exception occurred: {e}")
            return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
    else:
        return redirect(url_for('login_out.login_page'))


@user_blueprint.route('/delete_music', methods=['POST'])
def delete_music():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    music_id = data.get('music_id')

    if not music_id:
        return jsonify({'error': 'Missing music_id'}), 400

    connection.reconnect()
    cursor = connection.cursor(dictionary=True)

    try:
        # Start transaction
        cursor.execute("START TRANSACTION")

        # Get file names from the database
        cursor.execute('SELECT original, rendered FROM renderings WHERE music_id = %s', (music_id,))
        file_names = cursor.fetchone()
        print("musicid", music_id, file_names)

        if not file_names:
            return jsonify({'error': 'Music not found'}), 404

        original_path = os.path.join(UPLOAD_FOLDER, file_names['original']) if file_names['original'] else None
        rendered_path = os.path.join(RENDERED_FOLDER, file_names['rendered']) if file_names['rendered'] else None

        # Delete the database entry first
        cursor.execute('DELETE FROM renderings WHERE music_id = %s', (music_id,))
        connection.commit()  # Temporarily commit DB deletion

        # Try deleting the files if they exist
        try:
            if original_path and os.path.exists(original_path):
                print(original_path)
                os.remove(original_path)
            if rendered_path and os.path.exists(rendered_path):  # Only delete if file exists
                os.remove(rendered_path)
        except Exception as file_error:
            # Rollback the database deletion if file deletion fails
            connection.rollback()
            return jsonify({'error': f'Failed to delete files: {str(file_error)}'}), 500

        cursor.close()
        return jsonify({'success': 'Music deleted'}), 200

    except Exception as db_error:
        connection.rollback()  # Rollback if DB error occurs
        return jsonify({'error': f'Database error: {str(db_error)}'}), 500


@user_blueprint.route('/profile', methods=['GET'])
def get_profile():
    connection.reconnect()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('''SELECT * FROM users WHERE u_id = %s''', (session['u_id'],))
    user_data = cursor.fetchone()
    return render_template('user/user_profile.html', user=user_data)


@user_blueprint.route('/update_profile', methods=['POST'])
def update_profile():
    connection.reconnect()
    cursor = connection.cursor(dictionary=True)

    u_id = request.form.get("u_id")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    profile_pic = request.files.get("profile_pic")
    profile_pic_filename = None

    try:
        # Start transaction
        connection.start_transaction()

        # Handle profile picture upload
        if profile_pic and allowed_file(profile_pic.filename):
            profile_pic_filename = secure_filename(f"user_{u_id}_" + profile_pic.filename)
            profile_pic_path = os.path.join(r"E:\Main Project\FlaskEq\static\img\profile_pics", profile_pic_filename)
            profile_pic.save(profile_pic_path)

        # Update user data in the database
        query = """UPDATE users SET username=%s, email=%s, password=%s"""
        values = [username, email, password]

        if profile_pic_filename:
            query += ", profile_pic=%s"
            values.append(profile_pic_filename)

        query += " WHERE u_id=%s"
        values.append(u_id)

        cursor.execute(query, tuple(values))
        connection.commit()  # Commit the transaction if everything is fine
        session['username'] = username
        return jsonify({"message": "Profile updated successfully", "profile_pic": profile_pic_filename})

    except Exception as e:
        connection.rollback()  # Revert any changes if something goes wrong
        return jsonify({"error": "An error occurred. Changes reverted.", "details": str(e)}), 500
