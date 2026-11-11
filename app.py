"""Punto de entrada: `python app.py` levanta JASSHINE en http://127.0.0.1:5000"""
import os

from backend.jasshine import create_app

app = create_app()

if __name__ == "__main__":
    # debug solo para desarrollo local. Para publicar: JASSHINE_DEBUG=0 y un servidor real (gunicorn/waitress).
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("JASSHINE_DEBUG", "1") == "1")
