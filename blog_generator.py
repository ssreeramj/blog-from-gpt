import openai
import re
import numpy as np
import faiss
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from utils import log_error
import os
import logging
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

class Document:
    def __init__(self, page_content):
        self.page_content = page_content


def clean_text(text):
    """
    Clean the input text.
    """
    cleaned_text = re.sub(r' +', ' ', text, flags=re.DOTALL)
    cleaned_text = re.sub(r'[\x00-\x1F]', '', cleaned_text)
    cleaned_text = cleaned_text.replace('\n', ' ')
    cleaned_text = re.sub(r'\s*-\s*', '', cleaned_text)
    return cleaned_text

def adjust_chunk_sizes(docs, desired_chunk_size=1500, overlap=200):
    adjusted_docs = []
    temp_text = ""

    for doc in docs:
        temp_text += doc.page_content + " "
        if len(temp_text) >= desired_chunk_size:
            adjusted_docs.append(Document(temp_text.strip()))
            temp_text = temp_text[-overlap:]  # Keep the overlap for the next chunk

    if temp_text:
        adjusted_docs.append(Document(temp_text.strip()))

    return adjusted_docs

def split_text_into_chunks(text):
    """
    Split the cleaned text into manageable chunks using semantic chunking.
    """
    text_splitter = SemanticChunker(OpenAIEmbeddings(), breakpoint_threshold_type="interquartile")
    docs = text_splitter.create_documents([text])
    return docs

def get_embeddings(text_chunks):
    """
    Generate embeddings for each text chunk and print their shape and data type.
    """
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=[chunk.page_content for chunk in text_chunks]
    )

    # Extract embeddings
    embeddings = [item.embedding for item in response.data]

    return embeddings

def cluster_text_chunks(embeddings):
    """
    Cluster the text chunks based on their embeddings.
    """
    if not embeddings:
        raise ValueError("No valid embeddings to process.")

    vectors = np.array(embeddings).astype('float32')
    num_points = len(embeddings)
    num_clusters = min(num_points // 3, 10)
    dimension = vectors.shape[1]

    kmeans = faiss.Kmeans(dimension, num_clusters, niter=20, verbose=True)
    kmeans.train(vectors)
    centroids = kmeans.centroids
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)

    D, I = index.search(centroids, 1)
    sorted_array = np.sort(I, axis=0).flatten()
    return sorted_array

def summarize_section(section):
    """
    Summarize the given section of the blog while preserving the key narrative and information from the blog. Use simple one tier flat bullet list. 
    """
    logging.info("Entered Summary Section")
    model = ChatOpenAI(temperature=0, model="gpt-4o")
    output_parser = StrOutputParser()
    prompt = ChatPromptTemplate.from_template("Summarize the given section of the blog while preserving the key narrative and information from the blog. Use simple paragraph style and respond with only a concise and information heavy summar. Respond directly with the summary paragraphs.:\n\n{section}")
    chain = prompt | model | output_parser
    try:
        summary = chain.invoke(section)
        logging.info(f"GENERATED SUMMARY: {summary} \n\n")
        return summary
    except Exception as e:
        logging.info(f"ERROR GENERATING SUMMARY: {e}")

def extract_last_200_words(text):
    """
    Extract the last 200 words from the given text.
    """
    words = text.split()
    last_200 = " ".join(words[-200:])
    return last_200

def generate_blog_sections_from_chunks(docs):
    """
    Generate detailed blog sections from the selected text chunks using LangChain.
    """
    model = ChatOpenAI(temperature=0, model="gpt-4o", streaming=True)
    output_parser = StrOutputParser()

    prompt = ChatPromptTemplate.from_template("""
    You an expert content marketer. Write the continued sections for a summary blog that has the most useful and publishworthy information from the attached chat converstaion. Do not over exaggerate the conversation and strictly follow what has been discussed in the chat without adding any new information. Preserve the most important facts, terminologies, jargon, insights and information from the attached conversation between the user and ChatGPT. Don't mention user's name.
    Do not write full excerpts from the chat as they are. Summarise them concisely into paragraphs to write continued blog sections that have the best information from the chat. Ensure the new section fits naturally and flows seamlessly with the previous sections. Avoid repetitive information and maintain coherence.
    Writing style: Casual conversational, informational, insightful, deeply profound, engaging, talking directly to the reader, short simple linear active voice
    Do not use words like - [It's like, It's about, Isn't about, Isn't just, Delve, Imagine, consequently, in addition to, In conclusion, transformative, fostering, but also, not only]
    Write cohesive paragraph style blog style content. Write human like content with variable size paragraphs and natural conversational content flow.
    Use the summary of the content written till now to get context, use last 200 words to maintain flow and then use the chat messages to write fresh section content.
    Write on behalf of the user as if you are directly talking to the reader expressing your thoughts and inquiries. Remember to not write full information and only write the synthesised important parts based on the narrative. Wrie in book paragraphs.
    IMPORTANT: If any part is already included in previous sections as per the summary, then do not include it in the response. Skip it all together. Even if it means responding with a empty space character.
    IMPORTANT: Do not write long repetitive content and try to summarise chats by synthesising important information and writing concise summary paragraphs. Paragraphs should be long but total length should be short. 
                                              
    CURRENT BLOG PROGRESS & CHATS: 
    ```{text}```
    BLOG SECTION:
    """)
    chain = prompt | model | output_parser
    blog_content = ""
    summaries = []

    for i in tqdm(range(len(docs)), desc="Processing documents"):
        doc = docs[i]

        if i == 0:
            if len(docs) > 1:
                prompt_text = "[First part of chat with more to come]:\n\n[Chat Message by User]: " + doc.page_content
            else:
                prompt_text = "[First and only part of the chat]:\n\n[Chat Message by User]: " + doc.page_content
        elif i == len(docs) - 1:
            logging.info("Generating prompt data")
            last_200_words = " ".join(blog_content.split()[-200:])
            combined_context = "\n[Summary of blog content written till now]: \n" + "\n\n".join(summaries) + "\n\n[Last 200 words to maintain narrative]: " + last_200_words + "\n\n[Chat messages]: \n" + doc.page_content
            prompt_text = "[Last section of the blog]:\n\n" + combined_context
        else:
            logging.info("Generating prompt data")
            last_200_words = " ".join(blog_content.split()[-200:])
            combined_context = "\n[Summary of blog content written till now]: \n" + "\n\n".join(summaries) + "\n\n[Last 200 words to maintain narrative]: " + last_200_words + "\n\n[Chat messages]: \n" + doc.page_content
            prompt_text = "[Middle section of the blog]:\n\n" + combined_context

        try:
            logging.info(f"\nBLOG SECTION PROMPT: \n{prompt_text}")
            for chunk in chain.stream(prompt_text):
                if blog_content and not blog_content.endswith('\n'):
                    blog_content += '\n'
                yield chunk
                blog_content += chunk
            logging.info(f"Generated blog section number {i + 1}.")

            # Update summaries
            new_summary = summarize_section(blog_content)
            summaries = [new_summary]  # Update instead of append

        except Exception as e:
            log_error(f"Error generating blog content: {e}")

    logging.info("Completed generating all blog sections.")

def generate_blog_from_text(input_text):
    """
    Generate a detailed blog from the input text.
    """
    cleaned_text = clean_text(input_text)
    text_chunks = split_text_into_chunks(cleaned_text)
    for chunk in generate_blog_sections_from_chunks(text_chunks):
        yield chunk