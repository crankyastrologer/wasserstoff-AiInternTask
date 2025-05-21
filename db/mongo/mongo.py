from typing import List

from pymongo import MongoClient
import os

client = MongoClient(os.getenv("CONNECTION_STRING"))
db = client["user_text"]
collection = db["assignment"]


async def insert_into(data):
    try:
        res = collection.insert_one(data)
        print(res)
    except Exception as e:
        print(e)
        raise e


def get_specific_documents(username: str, document_id: List[str]):
    print("document_id argument:", document_id)
    print("type of document_id:", type(document_id))
    ans = collection.find({"username": username, "document_id": {"$in": document_id}}, {'_id': 0})

    return list(ans)


def get_single_documents(username: str, document_id: str):
    print("document_id argument:", document_id)
    print("type of document_id:", type(document_id))
    ans = collection.find({"username": username, "document_id": document_id}, {'_id': 0})

    return list(ans)


def get_all_documents(username: str):
    return collection.find({"username": username}, {'_id': 0})


def mongo_delete_document(username: str, document_id: str):

    return collection.delete_one({"username": username, "document_id": document_id})
