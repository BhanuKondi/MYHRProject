# routes/manager/manager_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.db import db
from models.models import Employee, User, Role, Leave,Holiday, LeaveSummary
from functools import wraps
from flask import Blueprint, render_template, session, redirect, flash, url_for, jsonify
from models.models import Employee, User, Role
from models.attendance import Attendance, IST
from models.db import db
from datetime import datetime, date

manager_attendance_bp = Blueprint(
    "manager_attendance_bp",
    __name__,
    url_prefix="/manager/attendance"
)

manager_bp = Blueprint("manager", __name__, url_prefix="/manager")

@manager_bp.route('/leave-management', methods=['GET', 'POST'])
def leave_management():
    user_id = session["user_id"]
    employee = Employee.query.filter_by(user_id=user_id).first()

    holidays = Holiday.query.all()
    leaves =  Leave.query.filter_by(emp_code=employee.emp_code).all()
    return render_template('manager/leave_management.html', holidays=holidays, leaves=leaves,employee=employee)
# ---------------- HOLIDAYS PAGE ----------------
@manager_bp.route("/holidays")
def holidays():
    holidays = Holiday.query.all()
    return render_template("manager/holidays.html", holidays=holidays)


# ---------------- REQUEST LEAVE ----------------
@manager_bp.route("/request-leave", methods=["GET", "POST"])
def request_leave():
    user_id = session["user_id"]
    employee = Employee.query.filter_by(user_id=user_id).first()

    if request.method == "POST":
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        reason = request.form["reason"]

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days + 1

        new_leave = Leave(
            emp_code=employee.emp_code,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason
        )

        db.session.add(new_leave)
        db.session.commit()

        flash("Leave request submitted successfully!", "success")
        return redirect(url_for("manager.track_requests"))

    return render_template("manager/request_leave.html", employee=employee)


# ---------------- TRACK MY REQUESTS ----------------
@manager_bp.route("/track-requests")
def track_requests():
    user_id = session["user_id"]
    employee = Employee.query.filter_by(user_id=user_id).first()

    leave_requests = Leave.query.filter_by(emp_code=employee.emp_code).all()

    return render_template("manager/track_requests.html", leaves=leave_requests)


# ---------------------------------------
# ---------------- Helper Function ----------------
def current_manager():
    """
    Returns the Employee object if the logged-in user is a manager.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    # Join Employee -> User -> Role to ensure the user is a manager
    mgr = (
        Employee.query
        .join(User)
        .join(Role)
        .filter(Employee.user_id == user_id, Role.name == "manager")
        .first()
    )
    print("mgr",mgr)
    return mgr


# ---------------- Login Required Decorator ----------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# ---------------- Dashboard Route ----------------
@manager_bp.route("/dashboard")
@login_required
def dashboard():
    mgr = current_manager()
    if not mgr:
        flash("Access denied: Not a manager.", "danger")
        return redirect("/login")

    # Example: get team members (employees that have manager_emp_id == mgr.id)
    team = Employee.query.filter_by(manager_emp_id=mgr.id).all()

    return render_template("manager/dashboard.html", manager=mgr, team=team)


# ---------------- Profile Routes ----------------
@manager_bp.route("/profile")
@login_required
def profile():
    mgr = current_manager()
    if not mgr:
        flash("Access denied: Not a manager.", "danger")
        return redirect("/login")
    return render_template("manager/profile.html", manager=mgr)


@manager_bp.route("/profile/edit", methods=["POST"])
@login_required
def profile_edit():
    mgr = current_manager()
    if not mgr:
        flash("Access denied: Not a manager.", "danger")
        return redirect("/login")

    phone = request.form.get("phone")
    address = request.form.get("address")
    display_name = request.form.get("display_name")

    if phone:
        mgr.phone = phone
    if address:
        mgr.address = address
    if display_name:
        user = User.query.get(mgr.user_id)
        user.display_name = display_name

    db.session.commit()
    flash("Profile updated successfully.", "success")
    return redirect(url_for("manager.profile"))



# --------------------------------------------------
# Helper: fetch logged-in manager
# --------------------------------------------------
def current_manager():
    user_id = session.get("user_id")
    if not user_id:
        return None

    return (
        Employee.query
        .join(User)
        .join(Role)
        .filter(Employee.user_id == user_id, Role.name == "manager")
        .first()
    )


# --------------------------------------------------
# Attendance UI Page (HTML)
# --------------------------------------------------
@manager_attendance_bp.route("/")
def attendance_page():
    mgr = current_manager()
    if not mgr:
        return redirect("/login")
    return render_template("manager/attendance.html", manager=mgr)


# --------------------------------------------------
# CLOCK-IN
# --------------------------------------------------
@manager_attendance_bp.route("/clock_in", methods=["POST"])
def clock_in():
    mgr = current_manager()
    if not mgr:
        return jsonify({"error": "Not logged in"}), 401

    today = date.today()
    count_today = Attendance.query.filter_by(user_id=mgr.user_id, date=today).count()
    now = datetime.now(IST)

    new_log = Attendance(
        user_id=mgr.user_id,
        transaction_no=count_today + 1,
        date=today,
        clock_in=now
    )
    db.session.add(new_log)
    db.session.commit()

    return jsonify({"success": True})


# --------------------------------------------------
# CLOCK-OUT
# --------------------------------------------------
@manager_attendance_bp.route("/clock_out", methods=["POST"])
def clock_out():
    mgr = current_manager()
    if not mgr:
        return jsonify({"error": "Not logged in"}), 401

    today = date.today()
    log = Attendance.query.filter_by(user_id=mgr.user_id, date=today, clock_out=None)\
                          .order_by(Attendance.id.desc()).first()

    if not log:
        return jsonify({"error": "No active session found"}), 400

    now = datetime.now(IST)
    log.finish(now)
    db.session.commit()

    return jsonify({"success": True})


# --------------------------------------------------
# CURRENT ACTIVE SESSION
# --------------------------------------------------
@manager_attendance_bp.route("/current")
def current_session():
    mgr = current_manager()
    if not mgr:
        return jsonify({"active": False})

    today = date.today()
    log = Attendance.query.filter_by(user_id=mgr.user_id, date=today, clock_out=None)\
                          .order_by(Attendance.id.desc()).first()

    if log:
        return jsonify({
            "active": True,
            "clock_in": log.clock_in.isoformat()
        })
    return jsonify({"active": False})


# --------------------------------------------------
# TODAY SUMMARY
# --------------------------------------------------
@manager_attendance_bp.route("/today-summary")
def today_summary():
    mgr = current_manager()
    if not mgr:
        return jsonify({"total_seconds": 0, "transactions": []})

    today = date.today()
    logs = Attendance.query.filter_by(user_id=mgr.user_id, date=today).order_by(Attendance.id.asc()).all()
    total_seconds = sum(log.duration_seconds or 0 for log in logs)

    transactions = []
    for log in logs:
        transactions.append({
            "transaction_no": log.transaction_no,
            "clock_in": log.clock_in.strftime("%I:%M:%S %p"),
            "clock_out": log.clock_out.strftime("%I:%M:%S %p") if log.clock_out else "-",
            "duration": log.duration_seconds or 0
        })

    return jsonify({
        "total_seconds": total_seconds,
        "transactions": transactions
    })
