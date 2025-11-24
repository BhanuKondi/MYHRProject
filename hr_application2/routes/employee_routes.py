from flask import Blueprint, render_template, session, redirect, url_for

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")

# Employee access check
@employee_bp.before_request
def check_employee():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role_id') != 3:  # Assuming Employee role_id = 3
        return "Access denied", 403

# ---------------- DASHBOARD ----------------
@employee_bp.route("/dashboard")
def dashboard():
    return render_template("employee/dashboard.html")
