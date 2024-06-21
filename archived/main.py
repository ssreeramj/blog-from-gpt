from fetcher import get_chat_url, fetch_html_content, extract_json_from_script, extract_messages
from processor import clean_and_format_messages, segment_messages
from blog_generator import generate_blog_sections
from utils import log_error
import logging

def main():
    chat_url = get_chat_url()
    logging.info(f"Fetching content from URL: {chat_url}")
    html_content = fetch_html_content(chat_url)
    
    if html_content:
        logging.info("HTML content fetched successfully.")
        json_data = extract_json_from_script(html_content)
        
        if json_data:
            logging.info("JSON data extracted successfully.")
            raw_messages = extract_messages(json_data)
            cleaned_messages = clean_and_format_messages(raw_messages)
            
            if cleaned_messages:
                logging.info(f"Extracted and cleaned {len(cleaned_messages)} messages.")
                segments = segment_messages(cleaned_messages, 20)  # Segment size of 20 messages
                blog_content = generate_blog_sections(segments)
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
    print(blog_content)

if __name__ == "__main__":
    main()