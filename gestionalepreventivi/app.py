from preventivi_app.database import initialize_database
from preventivi_app.ui import run


if __name__ == "__main__":
    initialize_database()
    run()
