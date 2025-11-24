from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from models.models import Employee, User
from models.db import db

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
