import json
from typing import List
from db.mongo import get_specific_documents
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)
message_cleaning = [
    (
        "system",
        "You are a helpful assistant that cleans up OCR-scanned text from documents. "
        "Your task is to refine the text by correcting spelling, fixing broken words or lines, "
        "removing artifacts, and making it readable — while preserving the original meaning. "
        "Do not change names or factual content."
        "Merge title and paragraph text into one paragraph for easier storage in vector store."
        "only return the refined text nothing else",
    ),
    ("human", "{paragraph}"),
]
query_refining = [
    (
        "system",
        """You are an assistant tasked with taking a natural language query from a user
    and converting it into a query for a vectorstore. In the process, strip out all 
    information that is not relevant for the retrieval task and return a new, simplified
    question for vectorstore retrieval. just return the query that can be use for searching not any more context
    Here is the user query: {question} """
    ),

]

rag_template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Use three sentences maximum and keep the answer as concise as possible.
Always say "thanks for asking!" at the end of the answer.

{context}

Question: {question}

Helpful Answer:"""

theme_extraction_1 = """
You are an expert document analyst. Your task is to extract themes from a single page of a document.

Instructions:
- Carefully read the provided page content.
- Identify any themes or subthemes present in the content.
- Summarize each identified theme concisely but clearly.
- If possible, include quotes or evidence from the content that support each theme.

Output Format:
(
  "page_number": <Page Number>,
  "themes": [
    (
      "title": "<Theme Title>",
      "summary": "<A short paragraph describing the theme>",
      "evidence": ["<Quoted text or description from page>"]
    ,)
    ...
  ])


Page Number: {page_number}
Page Content:
{page_text}
"""
theme_extraction_2 = """You are an expert analyst synthesizing themes across an entire document based on page-level analysis.

Instructions:
- Analyze the page-wise themes provided below.
- Identify recurring or coherent themes across the entire document.
- Merge overlapping or similar themes.
- For each theme, write a concise summary and list the pages that contribute evidence to it.
- Make sure the answer is in markdown format.

Output Format:
(
  "document_title": "{{document_title}}",
  "document_themes": [
   ( 
      "title": "<Theme Title>",
      "summary": "<Theme summary across the document>",
      "page_references": [<List of page numbers>]
    ),
    ...
  ]
)

Document Title: {document_title}
Page-Level Themes:
{page_themes}
"""

theme_extraction_3 = """You are a cross-document analysis expert. Your task is to synthesize themes across multiple documents and find coherent common themes.

Instructions:
- Analyze the document-level themes from multiple documents.
- Identify themes that appear across two or more documents.
- Group these into coherent cross-document themes.
- For each theme, provide a summary and specify which documents support it.
- Make sure the answer is in markdown format.
Output Format:
(
  "cross_document_themes": [
    (
      "title": "<Theme Title>",
      "summary": "<Brief synthesis across documents>",
      "document_references": ["<Document Title 1>", "<Document Title 2>", ...]
    ),
    ...
  ]
)

Document-Level Themes:
{document_theme_json_list}
"""
def refine_text(text):
    prompt = ChatPromptTemplate.from_messages(message_cleaning)
    chain = prompt | llm
    ans = chain.invoke({
        "paragraph": text
    })
    return ans


def refine_query(text):
    prompt = ChatPromptTemplate.from_messages(query_refining)
    chain = prompt | llm
    ans = chain.invoke({
        "question": text
    })
    return ans


def rag(query, context):
    prompt = ChatPromptTemplate.from_template(rag_template)
    chain = prompt | llm
    ans = chain.invoke({
        "context": context,
        "question": query
    })
    return ans


def find_themes(document_ids:List[str], username:str):
    docs = get_specific_documents(username,document_ids)
    dic = {}
    for doc in docs:
        ls = []
        for page in doc["pages"]:
            prompt = ChatPromptTemplate.from_template(theme_extraction_1)
            chain = prompt | llm
            ans = chain.invoke({
                "page_number": page["page"],
                "page_text": page["refined_text"]
            })
            ls.append(ans.content)

        prompt2 = ChatPromptTemplate.from_template(theme_extraction_2)
        chain2 = prompt2 | llm
        ans2 = chain2.invoke({
            "document_title": doc["filename"],
            "page_themes": json.dumps(ls)
        })
        dic[doc["document_id"]] = ans2.content
    if len(document_ids)==1:
        return dic[document_ids[0]]
    else:
        prompt3 = ChatPromptTemplate.from_template(theme_extraction_3)
        chain3 = prompt3 | llm
        ans3 = chain3.invoke({
            "document_theme_json_list": json.dumps(dic)
        })
        return ans3.content


