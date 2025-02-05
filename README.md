# Fynd Platform Assistant

This repository contains a FastAPI application that serves as a Fynd Platform Assistant. It provides a chat interface for users to interact with an AI assistant, as well as OAuth routes for authentication with the Fynd API.

## Architecture

The application is structured as follows:

- **FastAPI**: The main web framework used to build the application. It handles HTTP requests and responses.
- **OpenAI API**: Used to generate responses for the chat interface. The application streams responses from the OpenAI model.
- **SQLAlchemy**: Used for ORM (Object-Relational Mapping) to interact with the SQLite database. It manages `MerchantToken` and `StateStore` models.
- **HTTPX**: An asynchronous HTTP client used for making requests to external APIs, such as the Fynd API.
- **Jinja2**: Used for rendering HTML templates for the chat interface.
- **Environment Variables**: Managed using `python-dotenv` to load configuration settings from a `.env` file.

### Key Components

- **`main.py`**: The main application file containing route definitions and logic for handling chat and OAuth flows.
- **`models.py`**: Defines the database models and sets up the SQLite database.
- **`templates/chat.html`**: The HTML template for the chat interface, styled with Tailwind CSS.
- **`run.sh`**: A shell script to start the FastAPI server and manage logs.

## Running the Application

### Prerequisites

- Python 3.8 or higher
- SQLite
- An OpenAI API key

### Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies**

   Use `pip` to install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**

   Create a `.env` file in the root directory and add the following variables:

   ```
   OPENAI_API_KEY=your_openai_api_key
   FYND_API_KEY=your_fynd_api_key
   FYND_API_SECRET=your_fynd_api_secret
   EXTENSION_URL=your_extension_url
   ```

4. **Run the Application**

   Use the provided `run.sh` script to start the FastAPI server:

   ```bash
   ./run.sh
   ```

   This script will start the server and log output to `logs/backend.log`.

5. **Access the Application**

   Open your web browser and navigate to `http://localhost:8000` to access the chat interface.

### Additional Information

- **Logs**: Logs are stored in the `logs` directory. Use `tail -f logs/backend.log` to view logs in real-time.
- **Stopping the Server**: Use `kill $(cat logs/backend.pid)` to stop the server.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.