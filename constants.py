import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "")

if __name__ == "__main__":
    if API_KEY:
        lenght = len(API_KEY)
        mid = int(lenght / 2)
        print(f"API_KEY = {API_KEY[:mid]}{'*' * (lenght - mid)}")
    else:
        print("API_KEY не задан!")
