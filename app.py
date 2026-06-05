from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from config.database_config import mysql, app
from email_sender import send_unlock_email
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
from pathlib import Path
import os
import re

# Paths
current_dir = Path(__file__).parent
app.template_folder = str(current_dir / 'templates')
app.static_folder = str(current_dir / 'static')

bcrypt = Bcrypt(app)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
Session(app)

serializer = URLSafeTimedSerializer(app.secret_key)

# --- Validation Patterns ---
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$')

# Rate limiting config
# after 3 failed attempts, user gets a cooldown period
# after 3 cooldown rounds, account gets fully locked
MAX_FAILED_ATTEMPTS = 3
COOLDOWN_MINUTES = 1
MAX_COOLDOWN_ROUNDS = 3
ATTEMPT_EXPIRY_MINUTES = 5  # resets attempt count if idle for 5 mins


# --- Database Helpers ---

def get_user_by_email(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, password_hash, is_locked, created_at FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    return user


def get_login_attempts(ip_address, user_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT id, ip_address, user_id, failed_attempts, last_failed_attempt, cooldown_round "
        "FROM login_attempts WHERE ip_address=%s AND user_id=%s",
        (ip_address, user_id)
    )
    attempt = cur.fetchone()
    cur.close()
    return attempt


def create_login_attempt(ip_address, user_id):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO login_attempts (ip_address, user_id) VALUES (%s, %s)", (ip_address, user_id))
    mysql.connection.commit()
    cur.close()


def update_login_attempts(attempt_id, failed_attempts, last_attempt, cooldown_round):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE login_attempts SET failed_attempts=%s, last_failed_attempt=%s, cooldown_round=%s WHERE id=%s",
        (failed_attempts, last_attempt, cooldown_round, attempt_id)
    )
    mysql.connection.commit()
    cur.close()


def reset_login_attempts(attempt_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE login_attempts SET failed_attempts=0, cooldown_round=0, last_failed_attempt=NULL WHERE id=%s",
        (attempt_id,)
    )
    mysql.connection.commit()
    cur.close()


def lock_user_account(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_locked=TRUE WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()


def save_unlock_token(user_id, token):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO unlock_tokens (user_id, token) VALUES (%s, %s)", (user_id, token))
    mysql.connection.commit()
    cur.close()


# --- Validation Helpers ---

def is_valid_email(email):
    return EMAIL_REGEX.match(email)


def is_valid_password(password):
    return PASSWORD_REGEX.match(password)


# --- Rate Limiting Helpers ---

def reset_attempts_if_expired(login_attempt, now):
    attempt_id, _, _, failed_attempts, last_attempt, _ = login_attempt
    if last_attempt and failed_attempts > 0:
        if now > last_attempt + timedelta(minutes=ATTEMPT_EXPIRY_MINUTES):
            reset_login_attempts(attempt_id)
            return True
    return False


def reset_cooldown_if_expired(login_attempt, now):
    attempt_id, _, _, failed_attempts, last_attempt, cooldown_round = login_attempt
    if last_attempt and failed_attempts >= MAX_FAILED_ATTEMPTS:
        if now > last_attempt + timedelta(minutes=COOLDOWN_MINUTES):
            update_login_attempts(attempt_id, 0, last_attempt, cooldown_round)
            return True
    return False


def reset_cooldown_round_if_expired(login_attempt, now):
    attempt_id, _, _, failed_attempts, last_attempt, cooldown_round = login_attempt
    if last_attempt and cooldown_round > 0 and failed_attempts == 0:
        cooldown_end = last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
        if now > cooldown_end + timedelta(minutes=ATTEMPT_EXPIRY_MINUTES):
            cur = mysql.connection.cursor()
            cur.execute("UPDATE login_attempts SET cooldown_round=0 WHERE id=%s", (attempt_id,))
            mysql.connection.commit()
            cur.close()
            return True
    return False


def is_in_cooldown(login_attempt, now):
    _, _, _, failed_attempts, last_attempt, _ = login_attempt
    if last_attempt and failed_attempts >= MAX_FAILED_ATTEMPTS:
        return now <= last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
    return False


# --- Routes ---

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not is_valid_email(email):
            flash("Invalid email format.", "error")
            return redirect(url_for('register'))

        if not is_valid_password(password):
            flash("Password must be at least 8 characters with uppercase, lowercase, digit, and special character.", "error")
            return redirect(url_for('register'))

        # Backend confirm password check — catches tampered requests
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))

        if get_user_by_email(email):
            flash("An account with this email already exists.", "error")
            return redirect(url_for('register'))

        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, pw_hash))
        mysql.connection.commit()
        cur.close()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        ip_address = request.remote_addr

        if not is_valid_email(email):
            flash("Invalid email format.", "error")
            return redirect(url_for('login'))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for('login'))

        user = get_user_by_email(email)
        if not user:
            flash("No account found with that email.", "error")
            return redirect(url_for('login'))

        user_id, email, pw_hash, is_locked, created_at = user
        now = datetime.now()

        # Send unlock email if account is locked
        if is_locked:
            token = serializer.dumps(email)
            save_unlock_token(user_id, token)
            unlock_link = url_for('unlock_account', token=token, _external=True)
            send_unlock_email(email, unlock_link)
            flash("Your account is locked. An unlock link has been sent to your email.", "error")
            return redirect(url_for('login'))

        # Get or create attempt record
        login_attempt = get_login_attempts(ip_address, user_id)
        if not login_attempt:
            create_login_attempt(ip_address, user_id)
            login_attempt = get_login_attempts(ip_address, user_id)

        # Run expiry checks
        reset_attempts_if_expired(login_attempt, now)
        reset_cooldown_if_expired(login_attempt, now)
        reset_cooldown_round_if_expired(login_attempt, now)

        # Refresh after resets
        login_attempt = get_login_attempts(ip_address, user_id)
        attempt_id, _, _, failed_attempts, last_attempt, cooldown_round = login_attempt

        # Check cooldown
        if is_in_cooldown(login_attempt, now):
            cooldown_end = last_attempt + timedelta(minutes=COOLDOWN_MINUTES)
            remaining = int((cooldown_end - now).total_seconds())
            flash(f"Too many failed attempts. Try again in {remaining // 60}:{remaining % 60:02d}.", "error")
            return redirect(url_for('login'))

        # Verify password
        if bcrypt.check_password_hash(pw_hash, password):
            reset_login_attempts(attempt_id)
            session['user_id'] = user_id
            session.permanent = True
            return redirect(url_for('dashboard'))

        # Wrong password
        failed_attempts += 1

        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            cooldown_round += 1
            update_login_attempts(attempt_id, failed_attempts, now, cooldown_round)

            if cooldown_round >= MAX_COOLDOWN_ROUNDS:
                lock_user_account(user_id)
                token = serializer.dumps(email)
                save_unlock_token(user_id, token)
                unlock_link = url_for('unlock_account', token=token, _external=True)
                send_unlock_email(email, unlock_link)
                flash("Your account has been locked after too many failed attempts. Check your email to unlock.", "error")
            else:
                flash(f"Too many failed attempts from your IP. Wait {COOLDOWN_MINUTES} minute(s) before trying again.", "error")
        else:
            update_login_attempts(attempt_id, failed_attempts, now, cooldown_round)
            flash("Incorrect password. Please try again.", "error")

        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/unlock/<token>')
def unlock_account(token):
    try:
        email = serializer.loads(token, max_age=900)  # 15 min expiry
        user = get_user_by_email(email)
        if user:
            user_id, _, _, _, _ = user
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET is_locked=FALSE WHERE id=%s", (user_id,))
            cur.execute("DELETE FROM login_attempts WHERE user_id=%s", (user_id,))
            mysql.connection.commit()
            cur.close()
            flash("Your account has been unlocked. Please log in.", "success")
        else:
            flash("Invalid unlock link.", "error")
    except Exception:
        flash("This unlock link has expired. Please try logging in again to receive a new one.", "error")

    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
