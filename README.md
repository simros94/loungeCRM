# Prima Vista Lounge CRM - Backend

This is the backend for the Prima Vista Lounge CRM application, built with Flask.

## Project Structure

- `backend/`: Contains all backend-specific code.
  - `app.py`: Main Flask application setup, blueprint registration, CLI commands.
  - `database.py`: SQLAlchemy setup, database initialization function (`init_db`).
  - `models.py`: SQLAlchemy database models.
  - `routes/`: Directory containing Flask Blueprints for different features.
    - `auth.py`: Authentication routes (register, login, logout, status).
    - `checkin.py`: Passenger check-in route.
    - `dashboard.py`: Dashboard statistics and recent entries routes.
    - `passengers.py`: Passenger record management (search, exit).
    - `reports.py`: Lounge usage reports.
    - `reservations.py`: Reservation management routes.
    - `settings.py`: Lounge and user settings management routes.
  - `static/`: (If any backend-specific static files were needed, though frontend handles most static assets)
  - `templates/`: (If any backend-served HTML templates were needed)
  - `tests/`: Pytest unit and integration tests for the backend.
    - `conftest.py`: Pytest fixtures for test setup.
    - `test_*.py`: Test files for different modules/endpoints.
  - `requirements.txt`: Python dependencies for the backend.
  - `lounge.db`: SQLite database file (created when `flask init-db` is run).

## Setup and Installation

1.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies**:
    Navigate to the `backend` directory if your `requirements.txt` is inside it, or run from the project root if `requirements.txt` is at the root and paths in the app are relative. Assuming `requirements.txt` is in `backend/`:
    ```bash
    cd backend
    pip install -r requirements.txt
    cd .. 
    ```
    If `requirements.txt` is at the project root, just run `pip install -r requirements.txt` from the root.

3.  **Initialize the Database**:
    Ensure you are in the directory where `flask` commands can find your app (usually the project root or where `app.py`'s parent directory is added to PYTHONPATH). If `app.py` is in `backend/`, you might need to set `PYTHONPATH`.
    A common way if your app factory or app instance is discoverable:
    ```bash
    export FLASK_APP=backend.app  # Or backend:app if using factory pattern
    flask init-db
    ```
    This command will create the `lounge.db` SQLite database file with the defined schema.

## Running the Application

1.  **Set the Flask application environment variable**:
    ```bash
    export FLASK_APP=backend.app 
    export FLASK_ENV=development # Enables debug mode
    ```

2.  **Run the Flask development server**:
    ```bash
    flask run
    ```
    The application will typically be available at `http://127.0.0.1:5000/`.

## Running Tests

The backend includes a suite of tests using `pytest`.

1.  **Install testing dependencies** (if not already installed via `requirements.txt`):
    Make sure `pytest` and `pytest-flask` are in your `backend/requirements.txt` and installed.

2.  **Run tests**:
    Navigate to the project root directory (the one containing the `backend` folder).
    ```bash
    python -m pytest backend/tests
    ```
    Or, if you have `pytest` installed globally or in your virtual environment's path directly:
    ```bash
    pytest backend/tests
    ```

    This will discover and run all tests in the `backend/tests` directory. Each test typically uses a temporary, isolated database that is created and destroyed for that test, ensuring test independence.

## API Endpoints

(Refer to the `backend/routes/*.py` files for detailed API endpoint definitions and expected request/response formats.)

- **Authentication (`/auth`)**
  - `POST /register`: Register a new user.
  - `POST /login`: Log in an existing user.
  - `POST /logout`: Log out the current user.
  - `GET /status`: Get the authentication status of the current user.

- **Check-In (`/checkin`)**
  - `POST /`: Check in a passenger.

- **Dashboard (`/dashboard`)**
  - `GET /stats`: Get current lounge statistics.
  - `GET /recent-entries`: Get a list of recent lounge entries.

- **Passengers (`/passengers`)**
  - `GET /`: Get a list of passengers, with optional search query.
  - `POST /<int:entry_id>/exit`: Mark a passenger's lounge entry as exited.

- **Reservations (`/reservations`)**
  - `POST /`: Create a new reservation.
  - `GET /`: Get a list of reservations, with optional status filter.
  - `PUT /<int:reservation_id>/status`: Update the status of a reservation.

- **Settings (`/settings`)**
  - `GET /lounge`: Get current lounge settings.
  - `POST /lounge`: Update lounge settings (admin only).
  - `GET /users`: Get a list of users (admin only).
  - `POST /users`: Create a new user (admin only).
  - `PUT /users/<int:user_id>`: Update an existing user (admin only).

- **Reports (`/reports`)**
  - `GET /lounge-usage`: Get a report on lounge usage over a specified time period.
```
