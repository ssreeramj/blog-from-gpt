from dotenv import load_dotenv
from utils import log_error
import os
import openai
import logging
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
logging.info("Environment variables loaded and OpenAI API key set.")

model = ChatOpenAI(temperature=0, model="gpt-4o")
output_parser = StrOutputParser()

def generate_blog_sections(segments):
    """
    Function to generate blog sections for each segment of messages.
    """
    blog_content = ""

    for i, segment in enumerate(segments):
        logging.info(f"Processing segment {i + 1} of {len(segments)}.")
        
        if i == 0:
            prompt = f"""
            You are a helpful assistant. Write a detailed blog section based on the following text. Use the most useful and publishworthy information from the attached chat conversation. Use the user's messages and create a narrative from user's perspective about the curiosity they chase in the conversation. Preserve all the important facts, terminologies, jargon, insights and information from the conversation from the attached conversation between the user and ChatGPT. 
            Your result should be comprehensive and engaging, focusing on key points and relevant details. Avoid introductory phrases like 'In this passage'. Provide a natural flow of information that fits seamlessly into a blog.
            Writing style: Casual conversational, informational, insightful, deeply profound, engaging, talking directly to the reader, short simple linear active voice
            DO NOT USE THESE WORDS - [It's like, It's about, Isn't about, Isn't just, Delve, Imagine, consequently, in addition to, In conclusion, transformative, fostering, but also, not only]
            Write cohesive paragraph style blog style content. 
            Passage:
            {segment}
            BLOG SECTION:
            """
        else:
            prompt = f"""
            You are a helpful assistant. Continue writing a detailed blog that has the most useful and publishworthy information from the attached chat conversation. Preserve all the important facts, terminologies, jargon, insights and information from the conversation from the attached conversation between the user and ChatGPT. 
            Ensure the new section fits naturally and flows seamlessly with the previous sections. Avoid repetitive information and maintain coherence.
            Writing style: Casual conversational, informational, insightful, deeply profound, engaging, talking directly to the reader, short simple linear active voice
            DO NOT USE THESE WORDS  - [It's like, It's about, Isn't about, Isn't just, Delve, Imagine, consequently, in addition to, In conclusion, transformative, fostering, but also, not only]
            Write cohesive paragraph style blog style content. Write human like content with variable size paragraphs and natural conversational content flow. 
            Current Blog Content:
            {blog_content}

            New Messages:
            {segment}
            CONTINUE BLOG SECTION:
            """
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert content marketer and SEO friendly blog writer. You are designed to take chat conversations between users and ChatGPT and output detailed blog posts with insights and information from the provided user chat content."},
                    {"role": "user", "content": prompt}
                ]
            )
            blog_section = response.choices[0].message.content.strip()
            blog_content += blog_section + "\n\n"
            logging.info(f"Generated blog section {i + 1}.")
        except Exception as e:
            log_error(f"Error generating blog content: {e}")
    
    logging.info("Completed generating all blog sections.")
    return blog_content
