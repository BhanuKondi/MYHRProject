from flask import Flask, redirect, session
from werkzeug.security import generate_password_hash

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
        # Not logged in, go to login page
        return redirect("/login")
    else:
        # Logged in, redirect based on role
        if role_id == 1:  # Admin
            return redirect("/admin/dashboard")
        else:  # Employee
            return redirect("/employee/dashboard")

# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(debug=True)
