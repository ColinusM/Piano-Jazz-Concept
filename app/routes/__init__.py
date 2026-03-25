from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.api import api_bp


def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
