import os
from datetime import timedelta
from typing import Annotated, List
from fastapi import FastAPI, UploadFile, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel


from db.mongo import (
    get_specific_documents,
    get_all_documents,
    mongo_delete_document
)
from chat import (
    do_processing,
    insert_into_vectorstore,
    refine_query,
    rag,
    query_documents,
    process_image_file,
    delete_document_from_vectorstore,
    find_themes
)
from schema import (
    UserRegister,
    User,
    DocumentModel,
    QueryRequest,
    DocumentIDsRequest,
    Token
)
from auth import authenticate_user
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    register_user,
    get_current_user
)


app = FastAPI()


class FormData(BaseModel):
    username: str
    password: str


# CORS configuration
origins = [os.getenv("ORIGIN")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/uploadfiles/")
async def create_upload_files(
    files: list[UploadFile],
    current_user: Annotated[User, Depends(get_current_user)]
):
    parsed_documents = []
    uploaded_filenames = []

    for file in files:
        filename = file.filename.lower()

        try:
            if filename.endswith(".pdf"):
                doc = await do_processing(file, username=current_user.username)
            elif filename.endswith((".jpg", ".jpeg", ".png")):
                doc = await process_image_file(file, username=current_user.username)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")

            parsed_documents.append(DocumentModel(**doc["document"]))
            uploaded_filenames.append(doc["filename"])

        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            continue

    try:
        insert_into_vectorstore(parsed_documents, current_user.username)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting into vector store: {e}")

    return {"filenames": uploaded_filenames}


@app.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.post("/register/", status_code=201)
def register(user: Annotated[UserRegister, Form()]):
    try:
        return register_user(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")


@app.post("/vectorstore/add-documents")
async def add_documents(
    document_ids: List[str],
    current_user: Annotated[User, Depends(get_current_user)]
):
    try:
        username = current_user.username
        documents = get_specific_documents(username, document_ids)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {e}")


@app.get("/vectorstore/get_documents")
def get_documents(current_user: Annotated[User, Depends(get_current_user)]):
    try:
        username = current_user.username
        documents = list(get_all_documents(username))
        return {"documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {e}")


@app.post("/query")
def query_vectorstore(
    body: QueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        username = current_user.username
        refined_query = refine_query(body.query)

        if body.document_ids is None:
            documents = query_documents(refined_query.content, username)
        else:
            documents = query_documents(refined_query.content, username, document_ids=body.document_ids)

        response = rag(refined_query.content, documents)

        return {
            "documents": documents,
            "response": response.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@app.delete("/vectorstore/delete_document")
def delete_document(
    document_id: str,
    current_user: Annotated[User, Depends(get_current_user)]
):
    try:
        username = current_user.username
        delete_document_from_vectorstore(document_id, username)
        mongo_delete_document(username, document_id)
        return {"status": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")


@app.post("/get_themes")
def create_themes(
    current_user: Annotated[User, Depends(get_current_user)],
    request: DocumentIDsRequest
):
    try:
        username = current_user.username
        themes = find_themes(request.document_ids, username)
        return {"themes": themes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Theme extraction failed: {e}")


