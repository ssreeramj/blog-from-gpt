from fetcher import get_chat_url, fetch_html_content, extract_json_from_script, extract_messages
from processor import clean_and_format_messages, segment_messages
from blog_generator import generate_blog_from_text
from utils import log_error
import datetime
import logging

logging.basicConfig(filename=f'B_LOGS_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log', level=logging.INFO)

def main():
    chat_url = get_chat_url()
    logging.info(f"Fetching content from URL: {chat_url}")
    html_content = fetch_html_content(chat_url)
    
    if html_content:
        logging.info("HTML content fetched successfully.")
        json_data = extract_json_from_script(html_content)
        
        if json_data:
            raw_messages = extract_messages(json_data)
            cleaned_messages = clean_and_format_messages(raw_messages)
            
            if cleaned_messages:
                logging.info(f"Extracted and cleaned {len(cleaned_messages)} messages.")
                input_text = " ".join([msg['content'] for msg in cleaned_messages])
                blog_content = generate_blog_from_text(input_text)
                display_blog(blog_content)
            else:
                log_error("No valid messages to process.")
        else:
            log_error("Failed to extract JSON data from HTML content.")
    else:
        log_error("Failed to fetch HTML content from the provided URL.")

def display_blog(blog_content):
    """
    Function to print the blog content to the terminal.
    """
    logging.info("Displaying the generated blog content.")
    with open(f"blog_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w') as f:
        f.write(blog_content)

if __name__ == "__main__":
    main()

