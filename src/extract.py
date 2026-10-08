"""EXTRACT: descarga el CSV crudo y lo guarda en data/raw/."""
import requests

from config import RAW, URL


def extract() -> None:
    if "PEGA_AQUI" in URL:
        raise SystemExit("Edita src/config.py y pon el enlace real del CSV en URL.")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    print(f"[extract] Descargando {URL}")
    r = requests.get(URL, timeout=180)
    r.raise_for_status()
    RAW.write_bytes(r.content)
    print(f"[extract] Guardado en {RAW} ({RAW.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    extract()
