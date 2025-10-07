from app import create_app
from app.extensions import db
from app.models import User, Role
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    u = User.query.filter_by(username="admin").first()
    if not u:
        u = User(username="admin", email="admin@example.com")
        if hasattr(u, "set_password"):
            u.set_password("change-me-please")
        else:
            u.password_hash = generate_password_hash("change-me-please")
        # опционально подвяжем роль admin, если она есть
        try:
            r = Role.query.filter_by(name="admin").first()
            if r:
                try:
                    u.roles.append(r)  # если many-to-many
                except Exception:
                    u.role = r        # если one-to-many
        except Exception:
            pass
        db.session.add(u)
    db.session.commit()
    print("OK: admin user ready")
