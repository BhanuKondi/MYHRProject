from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from models.models import Employee, Leave, Holiday,LeaveSummary, db
from datetime import datetime

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")

# ---------------- ROLE CHECK ----------------
@employee_bp.before_request
def check_employee():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role_id") != 3:
        return "Access denied", 403

@employee_bp.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    employee = Employee.query.filter_by(user_id=user_id).first()

    if not employee:
        return "Employee record not found for this user", 404

    return render_template("employee/dashboard.html", employee=employee)
# ---------------- LEAVE MANAGEMENT HOME ----------------
@employee_bp.route('/leave-management', methods=['GET', 'POST'])
def leave_management():
    user_id = session["user_id"]
    employee = Employee.query.filter_by(user_id=user_id).first()

    holidays = Holiday.query.all()
    leaves =  Leave.query.filter_by(emp_code=employee.emp_code).all()
    return render_template('employee/leave_management.html', holidays=holidays, leaves=leaves,employee=employee)
# ---------------- HOLIDAYS PAGE ----------------
@employee_bp.route("/holidays")
def holidays():
    holidays = Holiday.query.all()
    return render_template("employee/holidays.html", holidays=holidays)


# ---------------- REQUEST LEAVE ----------------
@employee_bp.route("/request-leave", methods=["GET", "POST"])
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
        return redirect(url_for("employee.track_requests"))

    return render_template("employee/request_leave.html", employee=employee)


# ---------------- TRACK MY REQUESTS ----------------
@employee_bp.route("/track-requests")
def track_requests():
    user_id = session["user_id"]
    employee = Employee.query.filter_by(user_id=user_id).first()

    leave_requests = Leave.query.filter_by(emp_code=employee.emp_code).all()

    return render_template("employee/track_requests.html", leaves=leave_requests)