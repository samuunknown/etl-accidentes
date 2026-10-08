"""Ejecuta el pipeline completo: python src/run_pipeline.py"""
import argparse

from extract import extract
from load import load
from transform import run as transform_run


def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline ETL de incidentes viales")
    p.add_argument("--skip-extract", action="store_true",
                   help="Usar el CSV que ya está en data/raw/")
    args = p.parse_args()

    if not args.skip_extract:
        extract()
    df = transform_run()
    load(df)
    print("Pipeline terminado. Dashboard: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
