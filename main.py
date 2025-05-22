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
    """
    Process and store multiple uploaded files in the vector database.

    Supported formats:
    - PDF documents (processed with text extraction)
    - Images (JPG, JPEG, PNG - processed with OCR)

    Args:
        files: List of uploaded files from client
        current_user: Authenticated user object from JWT

    Returns:
        dict: List of successfully processed filenames

    Raises:
        HTTPException:
            400 - Unsupported file type
            500 - Vector store insertion error
    """
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
    """
       Authenticate user and generate JWT access token.

       Uses OAuth2 password flow for standard authentication.
       Token expires after 30 minutes by default (configurable).

       Args:
           form_data: Standard OAuth2 form containing username/password

       Returns:
           Token: Object containing JWT access token

       Raises:
           HTTPException:
               401 - Invalid credentials
       """
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
    """
      Register a new user account.

      Creates new user in database with hashed password.
      Returns same format as login for immediate authentication.

      Args:
          user: User registration data (username, password, etc.)

      Returns:
          Token: Access token for newly registered user

      Raises:
          HTTPException:
              500 - Registration failed (username taken, etc.)
      """
    try:
        return register_user(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")


@app.post("/vectorstore/add-documents")
async def add_documents(
    document_ids: List[str],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
        Add specific documents to user's vector store.

        Args:
            document_ids: List of MongoDB document IDs to add
            current_user: Authenticated user

        Returns:
            list: Retrieved document objects

        Raises:
            HTTPException:
                500 - Database retrieval error
        """
    try:
        username = current_user.username
        documents = get_specific_documents(username, document_ids)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {e}")


@app.get("/vectorstore/get_documents")
def get_documents(current_user: Annotated[User, Depends(get_current_user)]):
    try:
        """
          Retrieve all documents belonging to the authenticated user.

          Args:
              current_user: Authenticated user

          Returns:
              dict: { "documents": list of all user's documents }

          Raises:
              HTTPException: 
                  500 - Database error
          """
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
    """
      Query documents using RAG (Retrieval-Augmented Generation).

      Process flow:
      1. Refines the raw query for better search
      2. Retrieves relevant documents (either all or filtered by IDs)
      3. Generates response using the RAG model

      Args:
          body: Contains query text and optional document IDs filter
          current_user: Authenticated user

      Returns:
          dict: {
              "documents": list of relevant documents,
              "response": generated answer
          }

      Raises:
          HTTPException:
              500 - Query processing failed
      """
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
    """
    Delete a specific document from both vector store and database.

    Args:
        document_id: MongoDB ID of document to delete
        current_user: Authenticated user

    Returns:
        dict: Success message

    Raises:
        HTTPException:
            500 - Deletion failed
    """
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
    """
       Extract key themes from specified documents.

       Uses NLP processing to identify common themes/topics.

       Args:
           current_user: Authenticated user
           request: Contains list of document IDs to analyze

       Returns:
           dict: { "themes": list of identified themes }

       Raises:
           HTTPException:
               500 - Theme extraction failed
       """
    try:
        username = current_user.username
        themes = find_themes(request.document_ids, username)
        return {"themes": themes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Theme extraction failed: {e}")


