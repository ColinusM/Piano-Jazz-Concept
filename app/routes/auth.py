from flask import Blueprint, render_template, request, session, jsonify, redirect, current_app

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login')
def login_page():
    return render_template('login.html')


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if (data.get('username') == current_app.config['ADMIN_USERNAME'] and
            data.get('password') == current_app.config['ADMIN_PASSWORD']):
        session['admin'] = True
        session.pop('logged_out', None)
        session.permanent = bool(data.get('remember'))
        return jsonify({'success': True})
    return jsonify({'success': False}), 401


@auth_bp.route('/logout')
def logout():
    session.pop('admin', None)
    session['logged_out'] = True
    return redirect('/')


@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('admin', None)
    session['logged_out'] = True
    return jsonify({'success': True})
