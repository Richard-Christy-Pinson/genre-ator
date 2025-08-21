from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
import db_connection
admin_blueprint = Blueprint('admin_actions', __name__)
connection = db_connection.get_db_conn()


@admin_blueprint.route('/admin_dashboard')
def admin_dashboard():
    if session.get('username') == 'admin':
        connection.reconnect()
        cursor = connection.cursor(dictionary=True)

        # Total uploads (total rows in renderings)
        cursor.execute("SELECT COUNT(*) AS total_uploads FROM renderings")
        total_uploads = cursor.fetchone()['total_uploads']

        # Total renderings (non-empty 'rendered' column)
        cursor.execute(
            "SELECT COUNT(*) AS total_renderings FROM renderings WHERE rendered IS NOT NULL AND rendered != ''")
        total_renderings = cursor.fetchone()['total_renderings']

        # Find most used genre
        cursor.execute(""" SELECT g.genre, COUNT(r.genre_id) AS genre_count   FROM renderings r 
            JOIN genres g ON r.genre_id = g.genre_id GROUP BY r.genre_id ORDER BY genre_count DESC LIMIT 1 """)
        most_used_genre = cursor.fetchone()

        # Pass data to template
        return render_template(
            'admin/admin_dashboard.html',
            total_uploads=total_uploads,
            total_renderings=total_renderings,
            most_used_genre=most_used_genre['genre'] if most_used_genre else "None",
            genre_count=most_used_genre['genre_count'] if most_used_genre else 0
        )
    else:
        return redirect(url_for('login_out.login_page'))


@admin_blueprint.route('/admin/users_list')
def users_list():
    if session.get('username') == 'admin':
        connection.reconnect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""select * from users where username != 'admin'""")
        users = cursor.fetchall()
        return render_template('admin/users_list.html', users=users)
    else:
        return redirect(url_for('login_out.login_page'))


@admin_blueprint.route('/admin/eq_presets')
def eq_presets():
    if session.get('username') == 'admin':
        connection.reconnect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''SELECT  genres.genre, eq_levels.sub_bass, eq_levels.bass, eq_levels.lower_midrange, eq_levels.midrange, 
        eq_levels.upper_midrange, eq_levels.low_treble, eq_levels.treble, eq_levels.presence, eq_levels.brilliance, 
        eq_levels.air FROM eq_levels JOIN genres ON eq_levels.genre_id = genres.genre_id''')
        eq = cursor.fetchall()
        return render_template('admin/eq_presets_admin.html', eq_values=eq)
    else:
        return redirect(url_for('login_out.login_page'))


@admin_blueprint.route('/admin/save_eq_preset', methods=['POST'])
def save_eq_presets():
    if session.get('username') == 'admin':
        data = request.json  # Expecting JSON data from frontend
        # eg - > data = {'genre': 'Electronic', 'values': {'sub_bass': '4', 'bass': '12', 'lower_midrange': '2', 'midrange': '1', 'upper_midrange': '0', 'low_treble': '-1', 'treble': '-2', 'presence': '-3', 'brilliance': '-4', 'air': '-5'}}

        genre = data.get('genre')
        # Extract frequency values from nested dictionary
        values = data.get('values', {})  # Default to empty dict to avoid errors
        sub_bass = values.get('sub_bass')
        bass = values.get('bass')
        lower_midrange = values.get('lower_midrange')
        midrange = values.get('midrange')
        upper_midrange = values.get('upper_midrange')
        low_treble = values.get('low_treble')
        treble = values.get('treble')
        presence = values.get('presence')
        brilliance = values.get('brilliance')
        air = values.get('air')

        if not genre:
            return jsonify({'error': 'Missing genre_id'}), 400

        connection.reconnect()
        cursor = connection.cursor()
        cursor.execute('''select genre_id from genres where genre = %s''', (genre,))
        genre_id = cursor.fetchone()[0]

        update_query = ''' UPDATE eq_levels
            SET sub_bass = %s, bass = %s, lower_midrange = %s, midrange = %s, upper_midrange = %s,
                low_treble = %s, treble = %s, presence = %s, brilliance = %s, air = %s WHERE genre_id = %s '''
        cursor.execute(update_query, (sub_bass, bass, lower_midrange, midrange, upper_midrange,
                                      low_treble, treble, presence, brilliance, air, genre_id))
        connection.commit()
        return jsonify({'message': 'EQ Preset updated successfully'}), 200
    else:
        return jsonify({'error': 'Unauthorized'}), 403

@admin_blueprint.route('/admin/update_user_status', methods=['POST'])
def update_user_status():
    if session.get('username') == 'admin':
        data = request.json
        user_id = data.get("user_id")
        new_status = data.get("status")
        try:
            connection.reconnect()
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET status = %s WHERE u_id = %s", (new_status, user_id))
            connection.commit()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})


