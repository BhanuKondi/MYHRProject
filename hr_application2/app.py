from flask import Flask, redirect, session
from werkzeug.security import generate_password_hash
from datetime import date, datetime
from models.db import db
from models.models import Role, User, Employee

# ----------------- APP SETUP -----------------
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile("config.py")

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{app.config['MYSQL_USER']}:{app.config['MYSQL_PASSWORD']}"
    f"@{app.config['MYSQL_HOST']}/{app.config['MYSQL_DATABASE']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = app.config["SECRET_KEY"]

# ----------------- DATABASE -----------------
from models.db import db
db.init_app(app)

# ----------------- MODELS -----------------
from models.models import User, Role

# ----------------- DEFAULT ADMIN -----------------
def create_default_admin():
    with app.app_context():
        db.create_all()
        admin_role = Role.query.filter_by(name="Admin").first()
        if not admin_role:
            admin_role = Role(name="Admin")
            db.session.add(admin_role)
            db.session.commit()

        admin_email = "admin@example.com"
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                display_name="Administrator",
                role_id=admin_role.id,
                is_active=True,
                must_change_password=False
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("✔ Default admin created (admin@example.com / admin123)")

create_default_admin()
def create_default_employee():
    with app.app_context():
        db.create_all()

        # Ensure Employee role exists
        employee_role = Role.query.filter_by(name="Employee").first()
        if not employee_role:
            employee_role = Role(name="Employee")
            db.session.add(employee_role)
            db.session.commit()

        # Default employee account
        emp_email = "employee@example.com"
        employee_user = User.query.filter_by(email=emp_email).first()

        if not employee_user:
            employee_user = User(
                email=emp_email,
                display_name="Default Employee",
                role_id=employee_role.id,
                is_active=True,
                must_change_password=False
            )
            employee_user.set_password("emp123")
            db.session.add(employee_user)
            db.session.commit()
            print("✔ Default employee USER created")

        # Create employee profile
        emp_profile = Employee.query.filter_by(user_id=employee_user.id).first()

        if not emp_profile:
            emp_profile = Employee(
                emp_code="EMP005",                # must not be null
                user_id=employee_user.id,
                first_name="Default",
                last_name="Employee",
                work_email=emp_email,
                phone="9999999999",
                address="Hyderabad, India",
                date_of_joining=date.today(),     # required
                manager_emp_id=None,              # no manager
                status="Active",
                department="General",
                job_title="Staff",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            db.session.add(emp_profile)
            db.session.commit()
            print("✔ Default EMPLOYEE PROFILE created with all columns populated")
create_default_employee()

# ----------------- BLUEPRINTS -----------------
from auth.auth import auth_bp
from routes.admin_routes import admin_bp
from routes.settings import settings_bp
from routes.employee_routes import employee_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(employee_bp)

# ----------------- ROOT REDIRECT -----------------
@app.route("/")
def index():
    user_id = session.get("user_id")
    role_id = session.get("role_id")

    if not user_id:
        return redirect("/login")
    else:
        if role_id == 1:  # Admin
            return redirect("/admin/dashboard")
        else:  # Employee
            return redirect("/employee/dashboard")
# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(debug=True)
