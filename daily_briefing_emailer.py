
import os
import httpx
import smtplib
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "your_openweather_api_key")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "your_news_api_key")
WORDNIK_API_KEY = os.getenv("WORDNIK_API_KEY")  # Get your key from developer.wordnik.com

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = "RECEIVER_EMAIL"

CITIES = ["Casablanca", "Paris", "New York"]

# --- 1. Data Retrieval ---

def get_weather_data():
    """Fetches weather data for the specified cities."""
    weather_data = {}
    with httpx.Client() as client:
        for city in CITIES:
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
                weather_data[city] = {
                    "temp": data["main"]["temp"],
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"],
                }
            except httpx.HTTPStatusError as e:
                weather_data[city] = {"error": f"Could not retrieve weather: {e.response.status_code}"}
            except Exception as e:
                weather_data[city] = {"error": f"An error occurred: {e}"}
    return weather_data

def get_news_headlines():
    """Fetches top 3 technology news headlines."""
    try:
        with httpx.Client() as client:
            url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=3&apiKey={NEWSAPI_KEY}"
            response = client.get(url)
            response.raise_for_status()
            return response.json()["articles"]
    except httpx.HTTPStatusError as e:
        return [{"title": "Error fetching news", "description": f"Could not retrieve news: {e.response.status_code}"}]
    except Exception as e:
        return [{"title": "Error fetching news", "description": f"An error occurred: {e}"}]


def get_word_of_the_day():
    """Fetches the word of the day from Wordnik."""
    if not WORDNIK_API_KEY:
        return {"word": "N/A", "definition": "WORDNIK_API_KEY not set."}
    try:
        with httpx.Client() as client:
            url = f"https://api.wordnik.com/v4/words.json/wordOfTheDay?api_key={WORDNIK_API_KEY}"
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return {
                "word": data["word"],
                "definition": data["definitions"][0]["text"],
            }
    except httpx.HTTPStatusError as e:
        return {"word": "Error", "definition": f"Could not retrieve word of the day: {e.response.status_code}"}
    except Exception as e:
        return {"word": "Error", "definition": f"An error occurred: {e}"}

# --- 2. Formatting (Python 3.13 f-string features) ---

def create_email_body(weather_data, news_articles, word_of_the_day):
    """Creates the HTML body of the email using Python 3.13 f-strings."""

    # Helper to generate weather HTML
    def get_weather_html(city_name, data):
        if "error" in data:
            return f"""
                <div class="weather-city">
                    <h3>{city_name}</h3>
                    <p><i>{data['error']}</i></p>
                </div>
            """
        return f"""
            <div class="weather-city">
                <h3>{city_name}</h3>
                <img src="http://openweathermap.org/img/wn/{data['icon']}@2x.png" alt="Weather icon">
                <p>{data['temp']}°C, {data['description'].title()}</p>
            </div>
        """

    # Helper to generate news HTML
    def get_news_html(article):
        return f"""
            <div class="news-item">
                <h4><a href="{article.get('url', '#')}">{article.get('title', 'N/A')}</a></h4>
                <p>{article.get('description', 'No description available.')}</p>
            </div>
        """

    # Using Python 3.13's enhanced f-strings for cleaner multi-line HTML
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
            .container {{ background-color: #ffffff; padding: 20px; border-radius: 8px; max-width: 600px; margin: auto; }}
            .header {{ color: #333; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .section {{ margin-top: 20px; }}
            .section h2 {{ color: #555; }}
            .weather-container {{ display: flex; justify-content: space-around; text-align: center; }}
            .weather-city img {{ width: 50px; height: 50px; }}
            .news-item {{ border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; }}
            .news-item:last-child {{ border-bottom: none; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 0.8em; color: #888; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Daily Briefing</h1>
                <p>{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>

            <div class="section">
                <h2>Weather Forecast</h2>
                <div class="weather-container">
                    {
                        "".join([get_weather_html(city, data) for city, data in weather_data.items()])
                    }
                </div>
            </div>

            <div class="section">
                <h2>Top Tech Headlines</h2>
                {
                    "".join([get_news_html(article) for article in news_articles])
                }
            </div>

            <div class="section">
                <h2>Word of the Day</h2>
                <h3>{word_of_the_day.get('word', 'N/A').title()}</h3>
                <p>{word_of_the_day.get('definition', 'N/A')}</p>
            </div>

            <div class="footer">
                <p>This email was generated automatically.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# --- 3. Email Delivery ---

def send_email(html_content):
    """Sends the email."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("Email credentials not set. Skipping email delivery.")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Your Daily Briefing for {datetime.now().strftime('%B %d, %Y')}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg.set_content("Please enable HTML to view this email.", subtype="plain")
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP authentication failed. Check your email/password or app password.")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")


# --- Main Execution ---

if __name__ == "__main__":
    print("Fetching data for the daily briefing...")
    weather = get_weather_data()
    news = get_news_headlines()
    word_day = get_word_of_the_day()

    print("Creating email body...")
    email_body = create_email_body(weather, news, word_day)

    print("Sending email...")
    send_email(email_body)
    print("Script finished.")
