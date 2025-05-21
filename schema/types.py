from typing import List, Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None


class UserInDB(User):
    hashed_password: str


class UserRegister(BaseModel):
    username: str
    password: str


class Paragraph(BaseModel):
    paragraph: int
    refined_text: str


class Page(BaseModel):
    original_text: str
    page: int
    paragraphs: List[Paragraph]
    refined_text: str


class DocumentModel(BaseModel):
    document_id: str
    filename: str
    pages: List[Page]
    username: str


class QueryRequest(BaseModel):
    query: str
    document_ids: Optional[List[str]] = None


class DocumentIDsRequest(BaseModel):
    document_ids: List[str]
