"""Application factory for the Oral Surgeon Recruiting ATS."""
import os

from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the SQLite instance folder exists.
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints.
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.candidates import candidates_bp
    from app.routes.practices import practices_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(candidates_bp)
    app.register_blueprint(practices_bp)

    # Create tables and seed mock data on first run.
    with app.app_context():
        db.create_all()
        from app.seed import seed_if_empty

        seed_if_empty()

    # CLI helper: `flask --app run reseed` wipes and reseeds.
    @app.cli.command("reseed")
    def reseed():  # pragma: no cover - convenience command
        from app.seed import reseed as _reseed

        _reseed()
        print("Database reseeded with mock data.")

    return app
