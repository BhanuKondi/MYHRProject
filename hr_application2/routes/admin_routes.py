from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from models.models import Employee, User
from models.models import Holiday, Leave, LeaveSummary,LeaveApprovalConfig, User
from datetime import datetime
from models.db import db
from flask import request, jsonify
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from models.models import User
from models.attendance import Attendance
from sqlalchemy import func, and_
from calendar import monthrange

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Admin access check
@admin_bp.before_request
def check_admin():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role_id') != 1:  # Assuming Admin role_id = 1
        return "Access denied", 403

# ---------------- DASHBOARD ----------------
@admin_bp.route("/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")

# ---------------- EMPLOYEES LIST ----------------
@admin_bp.route("/employees")
def employees():
    search = request.args.get("search")
    query = Employee.query
    if search:
        query = query.filter(
            Employee.first_name.ilike(f"%{search}%") |
            Employee.last_name.ilike(f"%{search}%") |
            Employee.work_email.ilike(f"%{search}%")
        )
    all_employees = query.all()
    return render_template("admin/employees.html", employees=all_employees, search=search)

# ---------------- ADD EMPLOYEE ----------------
@admin_bp.route("/employees/add", methods=["POST"])
def add_employee():
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    work_email = request.form.get("work_email")
    emp_code = request.form.get("emp_code")
    role_id = request.form.get("role_id")
    temp_password = request.form.get("password")

    # VALIDATION
    if User.query.filter_by(email=work_email).first():
        flash("Email already exists. Please use another.", "danger")
        return redirect(url_for("admin.employees"))

    if Employee.query.filter_by(emp_code=emp_code).first():
        flash("Employee code already exists. Please use another.", "danger")
        return redirect(url_for("admin.employees"))

    # Create User
    user = User(email=work_email, display_name=f"{first_name} {last_name}", role_id=role_id, must_change_password=True)
    user.set_password(temp_password)
    db.session.add(user)
    db.session.commit()

    # Create Employee
    emp = Employee(
        emp_code=emp_code,
        first_name=first_name,
        last_name=last_name,
        work_email=work_email,
        phone=request.form.get("phone"),
        address=request.form.get("address"),
        date_of_joining=request.form.get("date_of_joining"),
        department=request.form.get("department"),
        job_title=request.form.get("job_title"),
        status="Active",
        user_id=user.id
    )
    db.session.add(emp)
    db.session.commit()
    flash(f"Employee {first_name} added successfully.", "success")
    return redirect(url_for("admin.employees"))

# ---------------- VIEW EMPLOYEE ----------------
@admin_bp.route("/employees/view/<int:id>")
def view_employee(id):
    emp = Employee.query.get(id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    return jsonify({
        "emp_code": emp.emp_code,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "work_email": emp.work_email,
        "phone": emp.phone,
        "department": emp.department,
        "job_title": emp.job_title,
        "address": emp.address,
        "date_of_joining": str(emp.date_of_joining),
        "status": emp.status
    })

# ---------------- EDIT EMPLOYEE ----------------
@admin_bp.route("/employees/edit/<int:id>", methods=["POST"])
def edit_employee(id):
    emp = Employee.query.get(id)
    if not emp:
        flash("Employee not found", "danger")
        return redirect(url_for("admin.employees"))

    work_email = request.form.get("work_email")
    emp_code = request.form.get("emp_code")

    if User.query.filter(User.email==work_email, User.id!=emp.user_id).first():
        flash("Email already exists. Please use another.", "danger")
        return redirect(url_for("admin.employees"))

    if Employee.query.filter(Employee.emp_code==emp_code, Employee.id!=id).first():
        flash("Employee code already exists. Please use another.", "danger")
        return redirect(url_for("admin.employees"))

    # Update Employee
    emp.first_name = request.form.get("first_name")
    emp.last_name = request.form.get("last_name")
    emp.work_email = work_email
    emp.phone = request.form.get("phone")
    emp.department = request.form.get("department")
    emp.job_title = request.form.get("job_title")
    emp.address = request.form.get("address")
    emp.status = request.form.get("status")

    # Update User
    user = User.query.get(emp.user_id)
    user.email = work_email
    user.display_name = f"{emp.first_name} {emp.last_name}"

    db.session.commit()
    flash("Employee updated successfully.", "success")
    return redirect(url_for("admin.employees"))
@admin_bp.route("/leaves")
def leaves_home():
    holidays = Holiday.query.order_by(Holiday.date).all()
    pending = Leave.query.filter_by(status="Pending").all()

    # ----- Build Leave Summary for ALL Employees -----
    employees = Employee.query.all()
    summaries = []

    for emp in employees:
        # Get all approved leaves for this employee
        approved_leaves = Leave.query.filter_by(emp_code=emp.emp_code, status="Approved").all()

        consumed = sum(l.total_days for l in approved_leaves)
        total_leaves = 24
        remaining = total_leaves - consumed

        summaries.append({
            "employee": emp,
            "total": total_leaves,
            "consumed": consumed,
            "remaining": remaining
        })

    return render_template(
        "admin/leaves.html",
        holidays=holidays,
        pending=pending,
        summaries=summaries
    )


@admin_bp.route('/update-leave-status/<int:leave_id>', methods=['POST'])
def update_leave_status(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    new_status = request.form.get('status')
    if new_status not in ['Approved', 'Rejected']:
        flash('Invalid status', 'danger')
        return redirect(url_for('admin.leaves_home'))

    leave.status = new_status
    db.session.commit()
    flash(f'Leave {new_status} successfully.', 'success')
    return redirect(url_for('admin.leaves_home'))


#Attendance

admin_attendance_bp = Blueprint("admin_attendance_bp", __name__, url_prefix="/admin/attendance")
IST = ZoneInfo("Asia/Kolkata")

# Helper: format seconds to HH:MM:SS
def fmt_seconds(sec):
    sec = int(sec or 0)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02}:{m:02}:{s:02}"

@admin_attendance_bp.route("/")
def attendance_page():
    return render_template("admin/attendance_list.html")

@admin_attendance_bp.route("/list_today")
def list_today():
    """Return JSON: one row per user for today's attendance"""
    today = datetime.now(IST).date()
    users = User.query.order_by(User.display_name).all()
    result = []

    for u in users:
        records = Attendance.query.filter_by(user_id=u.id, date=today).order_by(Attendance.clock_in).all()

        if not records:
            result.append({
                "user_id": u.id,
                "name": u.display_name,
                "date": str(today),
                "clock_in": "-",
                "clock_out": "-",
                "worked": "00:00:00",
                "status": "No Activity",
                "first_in_iso": None,
                "last_out_iso": None
            })
            continue

        # first in (earliest clock_in)
        first_in = min((r.clock_in for r in records if r.clock_in), default=None)
        # last out (latest clock_out) - can be None if user still active
        last_out_candidates = [r.clock_out for r in records if r.clock_out]
        last_out = max(last_out_candidates) if last_out_candidates else None

        total_seconds = sum((r.duration_seconds or 0) for r in records)
        status = "Active" if any(r.clock_out is None for r in records) else "Completed"

        result.append({
            "user_id": u.id,
            "name": u.display_name,
            "date": str(today),
            "clock_in": first_in.strftime("%I:%M:%S %p") if first_in else "-",
            "clock_out": last_out.strftime("%I:%M:%S %p") if last_out else "-",
            "worked": fmt_seconds(total_seconds),
            "status": status,
            "first_in_iso": first_in.isoformat() if first_in else None,
            "last_out_iso": last_out.isoformat() if last_out else None
        })

    return jsonify(result)

@admin_attendance_bp.route("/list_history")
def list_history():
    """
    Return JSON list of historical attendance summary rows.
    Optional query params:
      start_date=YYYY-MM-DD, end_date=YYYY-MM-DD
    By default returns last 30 days.
    """
    q = request.args
    try:
        if q.get("start_date"):
            start_date = datetime.fromisoformat(q.get("start_date")).date()
        else:
            start_date = (datetime.now(IST).date() - timedelta(days=30))
        if q.get("end_date"):
            end_date = datetime.fromisoformat(q.get("end_date")).date()
        else:
            end_date = datetime.now(IST).date()
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Query attendance grouped by date & user: compute first_in, last_out, total_seconds, status
    rows = []
    # fetch records in date range, ordered
    records = Attendance.query.filter(and_(Attendance.date >= start_date, Attendance.date <= end_date)).order_by(Attendance.date.desc(), Attendance.user_id).all()

    # group in memory (safe for moderate data). If large, implement DB group queries.
    grouped = {}
    for r in records:
        key = (r.date, r.user_id)
        grouped.setdefault(key, []).append(r)

    for (rdate, uid), recs in sorted(grouped.items(), reverse=True):
        user = User.query.get(uid)
        first_in = min((x.clock_in for x in recs if x.clock_in), default=None)
        last_out_candidates = [x.clock_out for x in recs if x.clock_out]
        last_out = max(last_out_candidates) if last_out_candidates else None
        total_seconds = sum((x.duration_seconds or 0) for x in recs)
        status = "Active" if any(x.clock_out is None for x in recs) else "Completed"

        rows.append({
            "date": rdate.isoformat(),
            "user_id": uid,
            "name": user.display_name if user else "Unknown",
            "clock_in": first_in.strftime("%I:%M:%S %p") if first_in else "-",
            "clock_out": last_out.strftime("%I:%M:%S %p") if last_out else "-",
            "worked": fmt_seconds(total_seconds),
            "status": status
        })

    # Also include users with no activity on a date? Usually we omit absent rows here;
    # the frontend can show absence based on missing entries for a date.
    return jsonify(rows)

@admin_attendance_bp.route("/transactions/<int:user_id>")
def attendance_transactions(user_id):
    """
    /admin/attendance/transactions/<user_id>?date=YYYY-MM-DD
    Returns all transactions for that user & date. Default = today
    """
    date_str = request.args.get("date")
    if date_str:
        try:
            the_date = datetime.fromisoformat(date_str).date()
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400
    else:
        the_date = datetime.now(IST).date()

    records = Attendance.query.filter_by(user_id=user_id, date=the_date).order_by(Attendance.clock_in).all()
    txns = []
    for r in records:
        txns.append({
            "transaction_no": r.transaction_no,
            "clock_in": r.clock_in.strftime("%I:%M:%S %p") if r.clock_in else "-",
            "clock_out": r.clock_out.strftime("%I:%M:%S %p") if r.clock_out else "-",
            "duration": fmt_seconds(r.duration_seconds or 0)
        })

    # last record summary
    last_record = None
    if records:
        latest = records[-1]
        last_record = {
            "clock_in": latest.clock_in.strftime("%I:%M:%S %p") if latest.clock_in else "-",
            "clock_out": latest.clock_out.strftime("%I:%M:%S %p") if latest.clock_out else "-",
            "worked": fmt_seconds(sum((x.duration_seconds or 0) for x in records)),
            "status": "Active" if any(x.clock_out is None for x in records) else "Completed"
        }

    return jsonify({"date": str(the_date), "transactions": txns, "last_record": last_record})

@admin_attendance_bp.route("/monthly/<int:user_id>/<int:year>/<int:month>")
def monthly_summary(user_id, year, month):
    """
    Return monthly summary for the user for given year and month.
    Computes days present (days with at least one record), days in month, total worked seconds,
    average hours, late days (first_in after office start), early leaves (last_out before office end).
    """
    # config: office start & end for late/early checks
    OFFICE_START = time(9, 30)   # 09:30 as example (adjust if needed)
    OFFICE_END = time(17, 30)    # 17:30 as example

    try:
        _, days_in_month = monthrange(year, month)
    except Exception:
        return jsonify({"error": "Invalid year/month"}), 400

    start_date = date(year, month, 1)
    end_date = date(year, month, days_in_month)

    # pull all attendance rows for that user in the month
    records = Attendance.query.filter(
        Attendance.user_id == user_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date, Attendance.clock_in).all()

    # group by date
    grouped = {}
    for r in records:
        grouped.setdefault(r.date, []).append(r)

    present_days = len(grouped)
    total_worked_seconds = sum((r.duration_seconds or 0) for r in records)

    late_days = 0
    early_leave_days = 0
    for d, recs in grouped.items():
        first_in = min((x.clock_in for x in recs if x.clock_in), default=None)
        last_out_candidates = [x.clock_out for x in recs if x.clock_out]
        last_out = max(last_out_candidates) if last_out_candidates else None
        if first_in and first_in.timetz().replace(tzinfo=None) > OFFICE_START:
            late_days += 1
        if last_out and last_out.timetz().replace(tzinfo=None) < OFFICE_END:
            early_leave_days += 1

    total_days = days_in_month
    absent_days = total_days - present_days
    avg_daily_seconds = (total_worked_seconds / present_days) if present_days else 0

    return jsonify({
        "user_id": user_id,
        "year": year,
        "month": month,
        "days_in_month": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "total_worked": fmt_seconds(total_worked_seconds),
        "avg_daily": fmt_seconds(int(avg_daily_seconds)),
        "late_days": late_days,
        "early_leaves": early_leave_days
    })


attendance_bp = Blueprint("attendance_bp", __name__, url_prefix="/attendance")

IST = ZoneInfo("Asia/Kolkata")
SHIFT_START_HOUR = 10  # 10 AM
SHIFT_END_HOUR = 6     # 6 AM next day

# ---------------------- Helper Functions ----------------------

def get_shift_date(now):
    """
    Returns the shift date for a timestamp considering 10AM - 6AM shift
    """
    if now.hour < SHIFT_END_HOUR:  # 12 AM - 5:59 AM → previous day's shift
        shift_day = (now - timedelta(days=1)).date()
    else:
        shift_day = now.date()
    return shift_day

def auto_close_previous(user_id):
    """
    Automatically closes any previous open attendance record
    """
    record = Attendance.query.filter_by(user_id=user_id, clock_out=None).first()
    if record:
        now = datetime.now(IST)
        ci = record.clock_in.replace(tzinfo=None)
        co = now.replace(tzinfo=None)
        record.clock_out = now
        record.duration_seconds = int((co - ci).total_seconds())
        db.session.commit()

# ---------------------- Routes ----------------------

@attendance_bp.route("/clock_in", methods=["POST"])
def clock_in():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login required"}), 401

    auto_close_previous(user_id)

    now = datetime.now(IST)
    shift_day = get_shift_date(now)

    # Shift start/end datetime
    shift_start_dt = now.replace(hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
    if now.hour < SHIFT_END_HOUR:
        shift_start_dt -= timedelta(days=1)
    shift_end_dt = shift_start_dt + timedelta(hours=20)  # 10 AM → 6 AM next day

    # Determine next transaction number
    last_txn = Attendance.query.filter_by(user_id=user_id, date=shift_day)\
        .order_by(Attendance.transaction_no.desc()).first()
    next_txn = (last_txn.transaction_no + 1) if last_txn else 1

    attendance = Attendance(
        user_id=user_id,
        transaction_no=next_txn,
        clock_in=now,
        date=shift_day,
        shift_start=shift_start_dt,
        shift_end=shift_end_dt
    )

    db.session.add(attendance)
    db.session.commit()

    return jsonify({"message": "Clocked In", "transaction_no": next_txn})

@attendance_bp.route("/clock_out", methods=["POST"])
def clock_out():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login required"}), 401

    open_record = Attendance.query.filter_by(user_id=user_id, clock_out=None).first()
    if not open_record:
        return jsonify({"error": "No active session"}), 400

    now = datetime.now(IST)
    ci = open_record.clock_in.replace(tzinfo=None)
    co = now.replace(tzinfo=None)

    open_record.clock_out = now
    open_record.duration_seconds = int((co - ci).total_seconds())
    db.session.commit()

    return jsonify({
        "message": "Clocked Out",
        "duration": open_record.duration_seconds,
        "clock_out": now.strftime("%d/%m/%Y, %I:%M:%S %p"),
        "transaction_no": open_record.transaction_no,
    })

@attendance_bp.route("/status", methods=["GET"])
def status():
    user_id = session.get("user_id")
    open_record = Attendance.query.filter_by(user_id=user_id, clock_out=None).first()
    return jsonify({"active": True if open_record else False})

@attendance_bp.route("/current", methods=["GET"])
def current_session():
    user_id = session.get("user_id")
    record = Attendance.query.filter_by(user_id=user_id, clock_out=None).first()
    if not record:
        return jsonify({"active": False})

    return jsonify({
        "active": True,
        "clock_in": record.clock_in.isoformat(),
        "shift_start": record.shift_start.isoformat(),
        "shift_end": record.shift_end.isoformat()
    })

@attendance_bp.route("/today-summary", methods=["GET"])
def today_summary():
    user_id = session.get("user_id")
    now = datetime.now(IST)
    shift_day = get_shift_date(now)

    records = Attendance.query.filter_by(user_id=user_id, date=shift_day)\
        .order_by(Attendance.transaction_no).all()
    total_seconds = sum(r.duration_seconds or 0 for r in records)

    hrs = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    formatted = f"{hrs:02}:{mins:02}:{secs:02}"

    transactions = [{
        "transaction_no": r.transaction_no,
        "clock_in": r.clock_in.strftime("%d/%m/%Y, %I:%M:%S %p"),
        "clock_out": r.clock_out.strftime("%d/%m/%Y, %I:%M:%S %p") if r.clock_out else "-",
        "duration": r.duration_seconds if r.duration_seconds else "-",
        "shift_start": r.shift_start.strftime("%d/%m/%Y, %I:%M:%S %p"),
        "shift_end": r.shift_end.strftime("%d/%m/%Y, %I:%M:%S %p")
    } for r in records]

    return jsonify({
        "worked": formatted,
        "total_seconds": total_seconds,
        "transactions": transactions,
    })

@admin_bp.route("/configure-approvals", methods=["GET", "POST"])
def configure_approvals():
    if session.get('role_id') != 1:
        return "Access denied", 403

    users = User.query.all()

    config = LeaveApprovalConfig.query.first()
    if not config:
        config = LeaveApprovalConfig()
        db.session.add(config)
        db.session.commit()

    if request.method == "POST":
        config.level1_approver_id = request.form.get("level1")
        config.level2_approver_id = request.form.get("level2")
        db.session.commit()

        flash("Approval workflow updated successfully!", "success")
        return redirect(url_for("admin.configure_approvals"))

    return render_template(
        "admin/configure_approvals.html",
        users=users,
        config=config
    )