from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models.models import User
from models.db import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password", "danger")
            return redirect(url_for('auth.login'))

        # Save session
        session['user_id'] = user.id
        session['email'] = user.email
        session['role_id'] = user.role_id

        # Force password change if required
        if user.must_change_password:
            flash("You must change your password before proceeding.", "warning")
            return redirect(url_for('settings.change_password'))

        # Role-based redirect
        if user.role.name.lower() == "admin":
            return redirect("/admin/dashboard")
        elif user.role.name.lower() == "manager":
            return redirect("manager/dashboard")
        else:
            return redirect("/employee/dashboard")  # create employee dashboard later

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
