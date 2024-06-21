import requests
from bs4 import BeautifulSoup
import json
from utils import log_error

def get_chat_url():
    """
    Function to get the chat URL from the user.
    """
    url = input("Please enter the ChatGPT public chat URL: ")
    return url

def fetch_html_content(url):
    """
    Function to fetch HTML content from the provided URL.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        return response.text
    except requests.exceptions.RequestException as e:
        log_error(f"Error fetching the HTML content: {e}")
        return None

def extract_json_from_script(html_content):
    """
    Function to extract and parse JSON content from script tags.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    script_elements = soup.find_all("script")
    
    for script_element in script_elements:
        script_content = script_element.string
        if script_content:
            try:
                json_content = json.loads(script_content)
                return json_content
            except json.JSONDecodeError:
                continue
    log_error("No valid JSON content found in script tags.")
    return None

def extract_messages(json_data):
    """
    Function to extract chat messages from the JSON data in sequence.
    """
    messages = []
    conversation = json_data.get("props", {}).get("pageProps", {}).get("serverResponse", {}).get("data", {}).get("linear_conversation", [])
    
    for message_data in conversation:
        message = message_data.get('message', {})
        author = message.get("author", {}).get("role", "unknown")
        content = message.get('content', {})
        parts = content.get('parts', [])
        
        for part in parts:
            if part and part != "Original custom instructions no longer available":
                messages.append((author, part))
    
    return messages
