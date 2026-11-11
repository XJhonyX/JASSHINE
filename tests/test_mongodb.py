import pytest

import backend.jasshine as jasshine
from backend.jasshine import create_app


def test_app_requires_mongodb_atlas_uri(monkeypatch):
    monkeypatch.setattr(jasshine, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("MONGODB_URI", raising=False)
    with pytest.raises(RuntimeError, match="Falta MONGODB_URI"):
        create_app({"MONGODB_URI": ""})
