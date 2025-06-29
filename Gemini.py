#!/usr/bin/env python3

from google.genai import types, errors
from google import genai
from time import sleep

class Interface:
    def __init__(self, model: str = "gemini-2.0-flash-lite", temperature: float = 1.0) -> None:

        # try importing the google API key
        try:
            with open("GOOGLE_API_KEY.txt") as file:
                self.API_KEY: str = file.readline()
        except Exception:
            try:
                import os
                self.API_KEY = os.environ["GOOGLE_API_KEY"]
            except Exception:
                raise ValueError("No API key detected")

        # some gemini models to choose from
        self.MODELS = {
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.5-pro-exp-03-25",
        }

        self.model: str = model
        self.attempts: int = 5
        self.temperature: float = temperature

    def generate(self, prompt: str) -> str:
        client = genai.Client(api_key=self.API_KEY)
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            temperature=self.temperature,
        )

        response: str = ""
        for chunk in client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=generate_content_config,
        ):
            response += chunk.text
        return response

    def safe_generate(self, prompt: str) -> str:
        for _ in range(self.attempts):
            try:
                response = self.generate(prompt)
                return response
            except errors.APIError as error:
                print(f"Error - code: {error.code}")
                print("Retrying in 15s...")
            sleep(15)
        return ""

    def set_api_key(self, key: str) -> None:
        self.API_KEY = key

    def set_model(self, model: str) -> None:
        self.model = model

    def set_temperature(self, temp: float) -> None:
        temp = min(2, max(0, temp))
        self.temperature = temp

# quick test code to check if API is functional
if __name__ == "__main__":
    intf = Interface("gemini-2.5-flash-preview-05-20")
    while (a := input(">>> ").lower()) != "q":
        print(intf.generate(a))
