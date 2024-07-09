# Standard library imports
import asyncio
import os
import random
import requests

# Third-party imports
from langchain_community.tools import DuckDuckGoSearchRun, DuckDuckGoSearchResults
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeColors
from langchain_core.tools import StructuredTool, tool
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langgraph.graph import END, MessageGraph, StateGraph
from langgraph.prebuilt import ToolInvocation
from langgraph.prebuilt.tool_executor import ToolExecutor
from typing import Annotated, Sequence, TypedDict, Union, Literal, List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SKLearnVectorStore

from pprint import pprint

from formatters import Section, Subsection, Outline, BlogSection, BlogSubSection
from scraper import ChatGPTScraper

from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = ChatOpenAI(name="gpt-4o")
EMBEDDINGS = OpenAIEmbeddings(model="text-embedding-3-small")
retriever = None


class ResearchState(TypedDict):
    blog_title: str
    full_conversation: str
    outline: Outline

    # The final sections output
    sections: List[BlogSection]
    article: str


async def refine_outline(state: ResearchState):
    refine_outline_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert blog writer. You have gathered information from experts. Now, you are writing an outline of blog article. \
    You need to make sure that the outline is comprehensive and specific. \
    Topic you are writing about: {topic} """,
            ),
            (
                "user",
                "Draft an outline based on the conversations with subject-matter experts:\n\nConversations:\n\n{conversations}\n\nWrite the outline for the blog:",
            ),
        ]
    )

    # Using turbo preview since the context can get quite long
    refine_outline_chain = refine_outline_prompt | LLM_MODEL.with_structured_output(
        Outline
    )
    updated_outline = await refine_outline_chain.ainvoke(
        {
            "topic": state["blog_title"],
            "conversations": state["full_conversation"],
        }
    )
    return {**state, "outline": updated_outline}


async def index_references(state: ResearchState):
    global retriever
    # Initialize the recursive text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=100,
        separators=["expert-1", "expert-2", "\n\n", "\n", "."],
    )

    # Chunk the long text
    chunks = text_splitter.split_text(state["full_conversation"])
    vectorstore = SKLearnVectorStore.from_texts(
        chunks,
        embedding=EMBEDDINGS,
    )
    retriever = vectorstore.as_retriever(k=7)
    return state


async def retrieve(inputs: dict):
    docs = await retriever.ainvoke(inputs["topic"] + ": " + inputs["section"])
    formatted = "\n".join(
        [
            f'<Document/>\n{doc.page_content}\n</Document>'
            for doc in docs
        ]
    )
    return {"docs": formatted, **inputs}


async def write_sections(state: ResearchState):

    section_writer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert blog writer. Complete your assigned blog section from the following outline:\n\n"
                "{outline}\n\nUse the following references:\n\n<Documents>\n{docs}\n<Documents>",
            ),
            ("user", "Write the full blog section for the {section} section."),
        ]
    )

    section_writer = (
        retrieve
        | section_writer_prompt
        | LLM_MODEL.with_structured_output(BlogSection)
    )

    outline = state["outline"]
    sections = await section_writer.abatch(
        [
            {
                "outline": outline.as_str,
                "section": section.section_title,
                "topic": state["blog_title"],
            }
            for section in outline.sections
        ]
    )
    return {
        **state,
        "sections": sections,
    }


async def write_article(state: ResearchState):
    writer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert blog author. Write the complete blog article on {topic} using the following section drafts:\n\n"
                "{draft}\n\nStrictly follow the blog outline guidelines.",
            ),
            (
                "user",
                'Write the complete blog article using markdown format.'
            ),
        ]
    )

    writer = writer_prompt | LLM_MODEL | StrOutputParser()

    topic = state["blog_title"]
    sections = state["sections"]
    draft = "\n\n".join([section.as_str for section in sections])
    article = await writer.ainvoke({"topic": topic, "draft": draft})
    return {
        **state,
        "article": article,
    }


def build_graph():
    workflow = StateGraph(ResearchState)

    nodes = [
        ("refine_outline", refine_outline),
        ("index_references", index_references),
        ("write_sections", write_sections),
        ("write_article", write_article),
    ]
    for i in range(len(nodes)):
        name, node = nodes[i]
        workflow.add_node(name, node)
        if i > 0:
            workflow.add_edge(nodes[i - 1][0], name)

    workflow.set_entry_point(nodes[0][0])
    workflow.add_edge(nodes[-1][0], END)
    blog_writer = workflow.compile()

    return blog_writer


async def get_final_article(chat_url=None):
    blog_writer = build_graph()

    scraper = ChatGPTScraper(url=chat_url)
    full_conversation = scraper.get_full_conversation()

    # print(f"Title: {scraper.title}")
    # print(f"Messages: {full_conversation[:300]}")

    response = await blog_writer.ainvoke({
        "blog_title": scraper.title,
        "full_conversation": full_conversation
    })

    # print(response.article)
    return response["article"]

if __name__ == "__main__":
    
    asyncio.run(get_final_article())