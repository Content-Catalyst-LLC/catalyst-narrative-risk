from dotenv import load_dotenv
load_dotenv()
from flask import Flask

def create_app():
    app = Flask(__name__)
    from app.routes.dev import bp as dev_bp
    app.register_blueprint(dev_bp)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}, 200

    return app
