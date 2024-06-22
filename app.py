from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from blog_generator import generate_blog_from_text
from fetcher import fetch_html_content, extract_json_from_script, extract_messages
from processor import clean_and_format_messages
import json
import logging
import datetime

logging.basicConfig(filename=f'B_LOGS_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log', level=logging.INFO)

app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def generate_blog_with_progress(chat_url):
    try:
        yield "data: " + json.dumps({"progress": 0, "status": "Initializing..."}) + "\n\n"
        
        yield "data: " + json.dumps({"progress": 10, "status": "Fetching content..."}) + "\n\n"
        html_content = fetch_html_content(chat_url)
        
        if html_content:
            yield "data: " + json.dumps({"progress": 30, "status": "Extracting data..."}) + "\n\n"
            json_data = extract_json_from_script(html_content)
            
            if json_data:
                yield "data: " + json.dumps({"progress": 50, "status": "Processing messages..."}) + "\n\n"
                raw_messages = extract_messages(json_data)
                cleaned_messages = clean_and_format_messages(raw_messages)
                
                if cleaned_messages:
                    yield "data: " + json.dumps({"progress": 70, "status": "Generating blog..."}) + "\n\n"
                    input_text = " ".join([msg['content'] for msg in cleaned_messages])
                    
                    for chunk in generate_blog_from_text(input_text):
                        yield "data: " + json.dumps({
                            "progress": 80,
                            "status": "Generating...",
                            "chunk": chunk
                        }) + "\n\n"
                    
                    yield "data: " + json.dumps({
                        "progress": 100,
                        "status": "Blog generated successfully!",
                        "chunk": None
                    }) + "\n\n"
                else:
                    yield "data: " + json.dumps({"progress": 100, "status": "Error: No valid messages to process."}) + "\n\n"
            else:
                yield "data: " + json.dumps({"progress": 100, "status": "Error: Failed to extract JSON data from HTML content."}) + "\n\n"
        else:
            yield "data: " + json.dumps({"progress": 100, "status": "Error: Failed to fetch HTML content from the provided URL."}) + "\n\n"
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        yield "data: " + json.dumps({"progress": 100, "status": f"Error: An error occurred while generating the blog: {str(e)}"}) + "\n\n"

@app.route('/generate-blog', methods=['POST'])
def generate_blog():
    chat_url = request.json['url']
    return Response(generate_blog_with_progress(chat_url), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)