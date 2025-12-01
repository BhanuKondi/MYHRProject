from .db import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    role = db.relationship("Role")

    def set_password(self, plain_password):
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password):
        return check_password_hash(self.password_hash, plain_password)

class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    work_email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_joining = db.Column(db.Date, nullable=False)
    manager_emp_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    status = db.Column(db.String(50), default="Active")
    department = db.Column(db.String(100))
    job_title = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Holiday(db.Model):
    __tablename__ = "holidays" 
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    day = db.Column(db.String(20))
    occasion = db.Column(db.String(100))


class Leave(db.Model):
    __tablename__ = "leaves"

    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(50), db.ForeignKey("employees.emp_code"), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer)
    reason = db.Column(db.String(200))
    status = db.Column(db.String(20), default="Pending")
    decision_date = db.Column(db.DateTime)

    employee = db.relationship("Employee", backref="leaves", foreign_keys=[emp_code])


class LeaveSummary(db.Model):
    __tablename__ = "leave_summary"

    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(50), db.ForeignKey("employees.emp_code"), nullable=False)

    total_leaves = db.Column(db.Integer, default=24)
    consumed = db.Column(db.Integer, default=0)
    pending = db.Column(db.Integer, default=24)

    employee = db.relationship("Employee", backref="leave_summary", lazy=True)

from models.attendance import Attendance