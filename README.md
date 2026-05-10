# CollabDocs API

A simple, fast, and secure backend API for creating workspaces, collaborating on documents, and managing team permissions. Built with Django and Django REST Framework.

**[DemoVideo](https://drive.google.com/file/d/13w9LqQzvTDKbf_MECFPDUvGmlTAoolFy/view?usp=drive_link)**

## Getting Started

Follow these steps to get the app running locally.

1. **Clone the project**
   Navigate to your chosen folder and open the project:
   ```bash
   cd collabdocs
   ```

2. **Set up Python**
   Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Set up your `.env` file securely:
   ```bash
   cp .env.example .env
   ```

5. **Start the Database**
   Fire up your PostgreSQL database using Docker:
   ```bash
   docker compose up -d
   ```

6. **Migrate the Database**
   Apply the Django database structure:
   ```bash
   python manage.py makemigrations core
   python manage.py migrate
   ```

7. **Run the Server**
   Start the application!
   ```bash
   python manage.py runserver
   ```
   The API will be live at `http://127.0.0.1:8001/api/`.

## Testing the API

To explore the endpoints, simply import the included `collabdocs.postman_collection.json` file directly into Postman.

- Create a user with the **Register** endpoint. This instantly returns a JWT token.
- Add the access token to your Postman Collection variables to authenticate all other requests.
- Explore creating workspaces, adding documents, tracking versions, and threading comments!
