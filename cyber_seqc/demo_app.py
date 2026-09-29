"""
Standalone demo entry point for the Secure Cybersecurity Gateway module.

Run this to test the module on its own:
    python demo_app.py

Then try, e.g.:
    curl http://localhost:5000/api/gateway/health
    curl http://localhost:5000/api/gateway/link/vsat-status
    curl http://localhost:5000/api/gateway/crypto/pqc/generate-keypair

To integrate into the FULL team website, in the main app file just do:
    from cybersecurity_gateway import gateway_bp
    app.register_blueprint(gateway_bp)
"""

from flask import Flask

from cybersecurity_gateway import gateway_bp

app = Flask(__name__)
app.register_blueprint(gateway_bp)


@app.route("/")
def index():
    return {
        "message": "Secure Cybersecurity Gateway demo is running.",
        "try": [
            "/api/gateway/health",
            "/api/gateway/link/vsat-status",
            "/api/gateway/link/reliability-report",
            "/api/gateway/crypto/pqc/generate-keypair",
        ],
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
