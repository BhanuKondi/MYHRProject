from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from models.models import Employee, Leave, User, Holiday,LeaveSummary, db,Leavee
from datetime import datetime

from flask import Blueprint, render_template, session, redirect, flash, url_for, jsonify
from models.models import Employee
from models.attendance import Attendance, IST
from models.db import db
from datetime import datetime, date

employee_attendance_bp = Blueprint(
    "employee_attendance_bp",
    __name__,
    url_prefix="/employee/attendance"
)

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
"""@employee_bp.route("/request-leave", methods=["GET", "POST"])
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

"""
from models.models import LeaveApprovalConfig

@employee_bp.route("/request-leave", methods=["GET", "POST"])
def request_leave():
    emp = current_employee()
    if not emp:
        flash("Employee record not found", "danger")
        return redirect(url_for("employee.dashboard"))

    # Fetch approver configuration
    config = LeaveApprovalConfig.query.first()
    if not config:
        flash("Approval workflow not configured by Admin.", "danger")
        return redirect(url_for("employee.dashboard"))

    if request.method == "POST":
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        reason = request.form["reason"]

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days + 1

        config = LeaveApprovalConfig.query.first()
        new_leave = Leavee(
            emp_code=emp.emp_code,
            start_date=start,
            end_date=end,
            total_days=total_days,
            reason=reason,
            status="PENDING_L1",
            level1_approver_id=config.level1_approver_id,
            level2_approver_id=config.level2_approver_id,
            current_approver_id=config.level1_approver_id
        )

        db.session.add(new_leave)
        db.session.commit()

        flash("Leave request submitted and sent to Level-1 approver.", "success")
        return redirect(url_for("employee.track_requests"))

    return render_template("employee/request_leave.html", employee=emp)

@employee_bp.route("/track-requests")
def track_requests():
    emp = current_employee()
    if not emp:
        flash("Employee record not found", "danger")
        return redirect(url_for("employee.dashboard"))

    leave_requests = Leavee.query.filter_by(emp_code=emp.emp_code).all()

    return render_template("employee/track_requests.html", leaves=leave_requests)
@employee_bp.route("/approvals")
def my_approvals():
    emp = current_employee()
    if not emp:
        flash("Employee not found", "danger")
        return redirect(url_for("employee.dashboard"))

    user_id = emp.user_id

    # Level-1 pending approvals
    pending_l1 = Leavee.query.filter_by(
        level1_approver_id=user_id,
        status="PENDING_L1"
    ).all()

    # Level-2 pending approvals
    pending_l2 = Leavee.query.filter_by(
        level2_approver_id=user_id,
        status="PENDING_L2"
    ).all()

    return render_template(
        "employee/my_approvals.html",
        pending_l1=pending_l1,
        pending_l2=pending_l2,
        employee=emp
    )
@employee_bp.route("/approve/<int:leave_id>", methods=["POST"])
def approve_leave(leave_id):
    emp = current_employee()
    if not emp:
        return "Unauthorized", 403

    user_id = emp.user_id
    leave = Leavee.query.get_or_404(leave_id)

    # Level 1 approval
    if leave.status == "PENDING_L1" and leave.level1_approver_id == user_id:
        leave.status = "PENDING_L2"
        leave.level1_decision_date = datetime.now()
        leave.current_approver_id = leave.level2_approver_id

    # Level 2 approval
    elif leave.status == "PENDING_L2" and leave.level2_approver_id == user_id:
        leave.status = "APPROVED"
        leave.level2_decision_date = datetime.now()
        leave.current_approver_id = None

    else:
        return "Invalid approval action", 403

    db.session.commit()
    flash("Leave approved successfully!", "success")
    return redirect(url_for("employee.my_approvals"))
@employee_bp.route("/reject/<int:leave_id>", methods=["POST"])
def reject_leave(leave_id):
    emp = current_employee()
    if not emp:
        return "Unauthorized", 403

    user_id = emp.user_id
    leave = Leavee.query.get_or_404(leave_id)

    if leave.status == "PENDING_L1" and leave.level1_approver_id == user_id:
        leave.status = "REJECTED_L1"
        leave.level1_decision_date = datetime.now()

    elif leave.status == "PENDING_L2" and leave.level2_approver_id == user_id:
        leave.status = "REJECTED_L2"
        leave.level2_decision_date = datetime.now()

    else:
        return "Invalid reject action", 403

    leave.current_approver_id = None
    db.session.commit()

    flash("Leave request rejected.", "warning")
    return redirect(url_for("employee.my_approvals"))

from sqlalchemy import func

@employee_bp.route("/leave-summary")
def leave_summary():
    emp = current_employee()
    if not emp:
        flash("Employee record not found", "danger")
        return redirect(url_for("employee.dashboard"))

    total_taken = db.session.query(func.sum(Leavee.total_days)) \
                    .filter_by(emp_code=emp.emp_code, status='APPROVED').scalar() or 0

    pending_l1 = db.session.query(func.sum(Leavee.total_days)) \
                    .filter_by(emp_code=emp.emp_code, status='PENDING_L1').scalar() or 0

    pending_l2 = db.session.query(func.sum(Leavee.total_days)) \
                    .filter_by(emp_code=emp.emp_code, status='PENDING_L2').scalar() or 0

    return render_template("employee/leave_summary.html",
                           total_taken=total_taken,
                           pending_l1=pending_l1,
                           pending_l2=pending_l2)
# --------------------------------------------------
# Helper: fetch logged-in employee
# --------------------------------------------------
def current_employee():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return Employee.query.filter_by(user_id=user_id).first()


# --------------------------------------------------
# Attendance UI Page (HTML)
# --------------------------------------------------
@employee_attendance_bp.route("/")
def attendance_page():
    emp = current_employee()
    if not emp:
        return redirect("/login")

    return render_template("employee/attendance.html", employee=emp)

@employee_bp.route("/profile", methods=["GET"])
def profile():
    emp = current_employee()
    return render_template("employee/profile.html", employee=emp)

@employee_bp.route("/profile/edit", methods=["POST"])

def profile_edit():
    emp = current_employee()

    phone = request.form.get("phone")
    address = request.form.get("address")
    display_name = request.form.get("display_name")

    if phone:
        emp.phone = phone
    if address:
        emp.address = address
    if display_name:
        user = User.query.get(emp.user_id)
        user.display_name = display_name

    db.session.commit()
    flash("Profile updated successfully.", "success")
    return redirect(url_for("employee.profile"))
# --------------------------------------------------
# API: Get employee’s own attendance list (JSON)
# --------------------------------------------------
@employee_attendance_bp.route("/list")
def attendance_list():
    emp = current_employee()
    if not emp:
        return jsonify([])

    logs = Attendance.query.filter_by(user_id=emp.user_id).order_by(Attendance.id.desc()).all()

    result = [
        {
            "id": log.id,
            "transaction_no": log.transaction_no,
            "date": log.date.strftime("%d-%m-%Y"),
            "clock_in": log.clock_in.strftime("%I:%M:%S %p"),
            "clock_out": log.clock_out.strftime("%I:%M:%S %p") if log.clock_out else "-",
            "worked": (
                f"{log.duration_seconds // 3600:02}:"
                f"{(log.duration_seconds % 3600) // 60:02}:"
                f"{log.duration_seconds % 60:02}"
                if log.duration_seconds else "00:00:00"
            )
        }
        for log in logs
    ]

    return jsonify(result)


# --------------------------------------------------
# CLOCK-IN
# --------------------------------------------------
@employee_attendance_bp.route("/clock_in", methods=["POST"])
def clock_in():
    emp = current_employee()
    if not emp:
        return redirect("/login")

    today = date.today()

    # Count how many logs today
    record_count = Attendance.query.filter_by(user_id=emp.user_id, date=today).count()

    now = datetime.now(IST)

    new_log = Attendance(
        user_id=emp.user_id,
        transaction_no=record_count + 1,
        date=today,
        clock_in=now
    )

    db.session.add(new_log)
    db.session.commit()

    flash("Clock-in successful!", "success")
    return redirect(url_for("employee_attendance_bp.attendance_page"))


# --------------------------------------------------
# CLOCK-OUT
# --------------------------------------------------
@employee_attendance_bp.route("/clock_out/<int:log_id>", methods=["POST"])
def clock_out(log_id):
    emp = current_employee()
    if not emp:
        return redirect("/login")

    log = Attendance.query.get(log_id)

    if not log or log.user_id != emp.user_id:
        flash("Invalid attendance record.", "danger")
        return redirect(url_for("employee_attendance_bp.attendance_page"))

    if log.clock_out:
        flash("Already clocked out.", "warning")
        return redirect(url_for("employee_attendance_bp.attendance_page"))

    now = datetime.now(IST)

    log.finish(now)
    db.session.commit()

    flash("Clock-out successful!", "success")
    return redirect(url_for("employee_attendance_bp.attendance_page"))
