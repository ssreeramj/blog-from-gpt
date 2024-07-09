import json

import requests
from bs4 import BeautifulSoup


class ChatGPTScraper:
    """
    A class to scrape and extract conversation data from a ChatGPT public chat URL.
    """

    def __init__(self, url: str):
        """
        Initialize the scraper with a URL.
        """
        self.url = url
        self.html_content = None
        self.json_data = None
        self.title = None
        self.messages = None

    @staticmethod
    def log_error(error_message):
        """
        Utility function to log errors.
        """
        print(f"Error: {error_message}")

    def fetch_html_content(self):
        """
        Fetch HTML content from the provided URL.
        """
        try:
            response = requests.get(self.url)
            response.raise_for_status()  # Check if the request was successful
            self.html_content = response.text
        except requests.exceptions.RequestException as e:
            self.log_error(f"Error fetching the HTML content: {e}")
            self.html_content = None

    def extract_json_from_script(self):
        """
        Extract and parse JSON content from script tags.
        """
        if not self.html_content:
            self.log_error("No HTML content to parse.")
            return

        soup = BeautifulSoup(self.html_content, "lxml")
        script_elements = soup.find_all("script")

        for script_element in script_elements:
            script_content = script_element.string
            if script_content:
                try:
                    self.json_data = json.loads(script_content)
                    return
                except json.JSONDecodeError:
                    continue
        self.log_error("No valid JSON content found in script tags.")
        self.json_data = None

    def extract_messages(self):
        """
        Extract chat messages from the JSON data in sequence.
        """
        if not self.json_data:
            self.log_error("No JSON data to extract messages from.")
            return

        messages = []

        conversation = (
            self.json_data.get("props", {})
            .get("pageProps", {})
            .get("serverResponse", {})
            .get("data", {})
            .get("linear_conversation", [])
        )
        self.title = (
            self.json_data.get("props", {})
            .get("pageProps", {})
            .get("serverResponse", {})
            .get("data", {})
            .get("title", "Empty Title")
        )

        for message_data in conversation:
            message = message_data.get("message", {})
            author = message.get("author", {}).get("role", "unknown")
            content = message.get("content", {})
            parts = content.get("parts", [])

            for part in parts:
                if part and part != "Original custom instructions no longer available":
                    messages.append((author, part))

        self.messages = messages

    def get_full_conversation(self) -> str:
        """
        Get the full conversation from the extracted messages.
        """
        self.fetch_html_content()
        self.extract_json_from_script()
        self.extract_messages()

        if not self.messages:
            self.log_error("No messages to format.")
            return ""

        full_conversation = ""
        for author, message in self.messages:
            full_conversation += (
                f"{'expert-1' if author == 'user' else 'expert-2'}: {message}\n\n"
            )
        return full_conversation


if __name__ == "__main__":
    CHAT_URL = "https://chatgpt.com/share/1d25bae0-fa33-4445-8276-b009a9bc28e1"

    scraper = ChatGPTScraper(url=CHAT_URL)
    full_conversation = scraper.get_full_conversation()

    print(f"Title: {scraper.title}")
    print(f"Messages: {full_conversation[:300]}")
