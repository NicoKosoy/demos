"""Abre cada sección de la app (sin navegador) y verifica que no tire errores."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

SECCIONES = ["Oportunidades", "Calculadora rápida", "Productos", "Proveedores", "Precios de mercado",
             "Configuración"]


@pytest.fixture
def base_temporal(tmp_path, monkeypatch):
    from mlglobal import config, db, demo
    monkeypatch.setattr(config, "DATOS_DIR", tmp_path)
    monkeypatch.setattr(db, "RUTA_DB", tmp_path / "base.sqlite")
    demo.cargar_ejemplos(db.conectar(tmp_path / "base.sqlite"))
    return tmp_path


@pytest.mark.parametrize("seccion", SECCIONES)
def test_seccion_sin_errores(base_temporal, seccion):
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=30)
    at.run()
    at.sidebar.radio[0].set_value(seccion).run()
    assert not at.exception, at.exception
