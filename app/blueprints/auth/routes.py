from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from . import bp
from .forms import LoginForm
from ...extensions import db
from ...models import User


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(username=form.username.data).first()
        if not user or not user.check_password(form.password.data) or not user.is_active:
            flash("Неверный логин/пароль или пользователь отключён", "danger")
            return render_template("auth/login.html", form=form)
        login_user(user, remember=True)
        flash("Добро пожаловать!", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("core.dashboard"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Вы вышли из системы", "info")
    return redirect(url_for("auth.login"))
