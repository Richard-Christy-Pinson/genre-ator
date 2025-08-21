import os

from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

import db_connection

login_out_blueprint = Blueprint('login_out', __name__)
connection = db_connection.get_db_conn()


@login_out_blueprint.route('/')
def login_page():
    if session.get('logged_in'):
        return redirect(url_for('user_actions.index'))
    else:
        return render_template('user/login.html')


@login_out_blueprint.route('/sign_in')
def sign_in():
    return render_template('user/user_reg.html')


@login_out_blueprint.route('/register', methods=['POST'])
def register_user():
    try:
        print("entered")
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        status = 1  # Default status

        # Handle Profile Picture Upload
        profile_pic = request.files['profile_pic'] if 'profile_pic' in request.files else None
        profile_pic_filename = None

        if profile_pic:
            filename = secure_filename(profile_pic.filename)
            profile_pic_filename = f"{username}_{filename}"  # Unique filename
            profile_pic.save(os.path.join('static/img/profile_pics/', profile_pic_filename))

        # Insert into MySQL
        query = "INSERT INTO users (username, email, password, profile_pic, status) VALUES (%s, %s, %s, %s, %s)"
        connection.reconnect()
        cursor = connection.cursor(dictionary=True)
        values = (username, email, password, profile_pic_filename, status)
        cursor.execute(query, values)
        connection.commit()

        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_out_blueprint.route('/login_action', methods=['POST'])
def login_action():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection.reconnect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            '''SELECT u_id, username, profile_pic, status FROM users WHERE username = %s AND password = %s''',
            (username, password))
        result = cursor.fetchone()
        if result:
            if result.get('status') == 0:
                return redirect(url_for('login_out.login_page'))
            session['username'] = result['username']
            session['u_id'] = result['u_id']
            session['profile_pic'] = result['profile_pic']
            print(session['profile_pic'])
            session['logged_in'] = True
            if result['username'] == 'admin':
                return redirect('/admin_dashboard')
            else:
                return redirect('/home')
        else:
            return redirect(url_for('login_out.login_page'))


@login_out_blueprint.route('/logout')
def logout():
    session.clear()
    return redirect('/')
