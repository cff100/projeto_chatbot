from pathlib import Path


PROJECT_ROOT_FOLDER = Path(__file__).parents[0].resolve()

DATA_FOLDER = PROJECT_ROOT_FOLDER / "data"

DATABASE_EXAMPLE = DATA_FOLDER / "database_example.db"

CENTRAL_DATABASE = DATA_FOLDER / "central_database.db"

CSV_FOLDER = DATA_FOLDER / "csv_files"