# Gemini API REST

A FastAPI-based REST API for interacting with Google Gemini models.

## Requirements

- Python 3.9+
- [Google Generative AI API key](https://ai.google.dev/)

## Installation

1. **Clone the repository** (if needed):

   ```sh
   git clone <your-repo-url>
   cd <your-project-folder>
   ```

2. **Create and activate a virtual environment:**

   ```sh
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   Create a `.env` file in the project root with the following content:

   ```
   GEMINI_API_KEY=your_google_api_key
   GEMINI_MODEL_ID=your_model_id
   ```

   Replace `your_google_api_key` and `your_model_id` with your actual credentials.

5. **Run the API:**

   ```sh
   uvicorn GeminiAPIRest:app --reload
   ```

   The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Usage

Send a POST request to `/asistente/` with a JSON body:

```json
{
  "text": "Tu pregunta aquí"
}
```

## License

MIT
