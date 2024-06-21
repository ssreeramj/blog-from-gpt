import logging

def clean_and_format_messages(messages):
    """
    Function to clean and format messages for further processing.
    """
    cleaned_messages = []
    for author, message in messages:
        cleaned_messages.append({
            "role": "User" if author == "user" else "ChatGPT",
            "content": "\n[User]: " + message.strip() if author == "user" else "\n\n[ChatGPT Response]: " + message.strip()
        })
    return cleaned_messages

def segment_messages(messages, segment_size):
    """
    Function to segment messages into chunks of a specified size.
    """
    segments = []
    for i in range(0, len(messages), segment_size):
        segment = messages[i:i + segment_size]
        segments.append(segment)
    logging.info(f"Segmented messages into {len(segments)} segments.")
    return segments
