import json
import logging
from collections.abc import AsyncGenerator

import fastapi
from fastapi import HTTPException
from sqlalchemy import select

from fastapi_app.api_models import (
    ChatRequest,
    ErrorResponse,
    ItemPublic,
    ItemWithDistance,
    RetrievalResponse,
    RetrievalResponseDelta,
)
from fastapi_app.dependencies import ChatClient, CommonDeps, DBSession, EmbeddingsClient
from fastapi_app.postgres_models import Item
from fastapi_app.postgres_searcher import PostgresSearcher

router = fastapi.APIRouter()


async def format_as_ndjson(r: AsyncGenerator[RetrievalResponseDelta, None]) -> AsyncGenerator[str, None]:
    """
    Format the response as NDJSON
    """
    try:
        async for event in r:
            yield event.model_dump_json() + "\n"
    except Exception as error:
        logging.exception("Exception while generating response stream: %s", error)
        yield json.dumps({"error": str(error)}, ensure_ascii=False) + "\n"


@router.get("/items/{id}", response_model=ItemPublic)
async def item_handler(database_session: DBSession, id: int) -> ItemPublic:
    """A simple API to get an item by ID."""
    item = (await database_session.scalars(select(Item).where(Item.id == id))).first()
    if not item:
        raise HTTPException(detail=f"Item with ID {id} not found.", status_code=404)
    return ItemPublic.model_validate(item.to_dict())


@router.get("/similar", response_model=list[ItemWithDistance])
async def similar_handler(
    context: CommonDeps, database_session: DBSession, id: int, n: int = 5
) -> list[ItemWithDistance]:
    """A similarity API to find items similar to items with given ID."""
    item = (await database_session.scalars(select(Item).where(Item.id == id))).first()
    if not item:
        raise HTTPException(detail=f"Item with ID {id} not found.", status_code=404)

    closest = await database_session.execute(
        select(Item, Item.embedding_ada002.l2_distance(item.embedding_ada002))
        .filter(Item.id != id)
        .order_by(Item.embedding_ada002.l2_distance(item.embedding_ada002))
        .limit(n)
    )
    return [
        ItemWithDistance.model_validate(item.to_dict() | {"distance": round(distance, 2)}) for item, distance in closest
    ]


@router.get("/search", response_model=list[ItemPublic])
async def search_handler(
    context: CommonDeps,
    database_session: DBSession,
    openai_embed: EmbeddingsClient,
    query: str,
    top: int = 5,
    enable_vector_search: bool = True,
    enable_text_search: bool = True,
) -> list[ItemPublic]:
    """A search API to find items based on a query."""
    searcher = PostgresSearcher(
        db_session=database_session,
        openai_embed_client=openai_embed.client,
        embed_deployment=context.openai_embed_deployment,
        embed_model=context.openai_embed_model,
        embed_dimensions=context.openai_embed_dimensions,
        embedding_column=context.embedding_column,
    )
    results = await searcher.search_and_embed(
        query, top=top, enable_vector_search=enable_vector_search, enable_text_search=enable_text_search
    )
    return [ItemPublic.model_validate(item.to_dict()) for item in results]


# @router.post("/chat", response_model=RetrievalResponse | ErrorResponse)
# async def chat_handler(
#     context: CommonDeps,
#     database_session: DBSession,
#     openai_embed: EmbeddingsClient,
#     openai_chat: ChatClient,
#     chat_request: ChatRequest,
# ):
#     try:
#         searcher = PostgresSearcher(
#             db_session=database_session,
#             openai_embed_client=openai_embed.client,
#             embed_deployment=context.openai_embed_deployment,
#             embed_model=context.openai_embed_model,
#             embed_dimensions=context.openai_embed_dimensions,
#             embedding_column=context.embedding_column,
#         )
#         rag_flow: SimpleRAGChat | AdvancedRAGChat
#         if chat_request.context.overrides.use_advanced_flow:
#             rag_flow = AdvancedRAGChat(
#                 searcher=searcher,
#                 openai_chat_client=openai_chat.client,
#                 chat_model=context.openai_chat_model,
#                 chat_deployment=context.openai_chat_deployment,
#             )
#         else:
#             rag_flow = SimpleRAGChat(
#                 searcher=searcher,
#                 openai_chat_client=openai_chat.client,
#                 chat_model=context.openai_chat_model,
#                 chat_deployment=context.openai_chat_deployment,
#             )

#         chat_params = rag_flow.get_params(chat_request.messages, chat_request.context.overrides)

#         contextual_messages, results, thoughts = await rag_flow.prepare_context(chat_params)
#         response = await rag_flow.answer(
#             chat_params=chat_params, contextual_messages=contextual_messages, results=results, earlier_thoughts=thoughts
#         )
#         return response
#     except Exception as e:
#         return {"error": str(e)}
import numpy as np
import openai
import pandas as pd
import psycopg2
from openai import AzureOpenAI


@router.post("/chat", response_model=RetrievalResponse | ErrorResponse)
async def chat_handler(
    context: CommonDeps,
    database_session: DBSession,
    openai_embed: EmbeddingsClient,
    openai_chat: ChatClient,
    chat_request: ChatRequest,
):
    try:
        # Step 1: Set up the Postgres connection
        conn_params = {
            "dbname": context.postgres_dbname,
            "user": context.postgres_user,
            "password": context.postgres_password,
            "host": context.postgres_host,
            "port": context.postgres_port,
        }

        # Step 2: Create embeddings using the input question
        question = chat_request.messages[-1].content
        openai.api_type = "azure"
        openai.api_base = context.openai_endpoint
        openai.api_key = context.openai_key
        openai.api_version = context.openai_version

        def create_embeddings(query):
            try:
                response = openai.embeddings.create(input=query, model=context.openai_embed_deployment)
                embedding = response.data[0].embedding
                return np.array(embedding)
            except Exception as e:
                print(f"Error generating embeddings: {e}")
                return None

        embedding = create_embeddings(question)
        if embedding is None:
            return {"error": "Failed to generate embedding"}

        # Step 3: Execute SQL function to rank results based on embeddings
        def execute_rerank_function(embedding, query, top_n, consider_n):
            try:
                with psycopg2.connect(**conn_params) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT * FROM get_vector_rerank_pagerank_rrf2_cases(%s, %s, %s, %s);
                        """,
                            (embedding, query, top_n, consider_n),
                        )

                        results = cursor.fetchall()
                        colnames = [desc[0] for desc in cursor.description]
                        return pd.DataFrame(results, columns=colnames)
            except psycopg2.Error as e:
                print(f"Error executing SQL function: {e}")
                return None

        results_df = execute_rerank_function(embedding, question, top_n=5, consider_n=10)
        if results_df is None or results_df.empty:
            return {"error": "No relevant cases found"}

        # Step 4: Generate legal insights using OpenAI Chat

        client = AzureOpenAI(
            azure_endpoint=context.openai_endpoint, api_key=context.openai_key, api_version=context.openai_version
        )

        def generate_legal_response(question, context):
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a Legal Research AI Assistant that helps people understand relevant legal cases. Answer the user's QUESTION below using provided cases in the CONTEXT section. Keep your answer grounded in the cases in the CONTEXT section. If the CONTEXT section doesn’t contain the facts to answer the QUESTION, return NONE. Identify top 2 legal principles used in the cases provided, explain them and group prominent cases by those principles.""",
                    },
                    {"role": "user", "content": f"QUESTION: {question}\nCONTEXT: {context}"},
                ],
                max_tokens=800,
                temperature=0.3,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=False,
            )
            return completion.choices[0].message.content

        context_json = results_df.to_json(orient="records")
        response_text = generate_legal_response(question, context_json)

        # Step 5: Return the AI-generated legal response
        return {"message": response_text}

    except Exception as e:
        return {"error": str(e)}


# @router.post("/chat/stream")
# async def chat_stream_handler(
#     context: CommonDeps,
#     database_session: DBSession,
#     openai_embed: EmbeddingsClient,
#     openai_chat: ChatClient,
#     chat_request: ChatRequest,
# ):
#     searcher = PostgresSearcher(
#         db_session=database_session,
#         openai_embed_client=openai_embed.client,
#         embed_deployment=context.openai_embed_deployment,
#         embed_model=context.openai_embed_model,
#         embed_dimensions=context.openai_embed_dimensions,
#         embedding_column=context.embedding_column,
#     )

#     rag_flow: SimpleRAGChat | AdvancedRAGChat
#     if chat_request.context.overrides.use_advanced_flow:
#         rag_flow = AdvancedRAGChat(
#             searcher=searcher,
#             openai_chat_client=openai_chat.client,
#             chat_model=context.openai_chat_model,
#             chat_deployment=context.openai_chat_deployment,
#         )
#     else:
#         rag_flow = SimpleRAGChat(
#             searcher=searcher,
#             openai_chat_client=openai_chat.client,
#             chat_model=context.openai_chat_model,
#             chat_deployment=context.openai_chat_deployment,
#         )

#     chat_params = rag_flow.get_params(chat_request.messages, chat_request.context.overrides)

#     # Intentionally do this before we stream down a response, to avoid using database connections during stream
#     # See https://github.com/tiangolo/fastapi/discussions/11321
#     contextual_messages, results, thoughts = await rag_flow.prepare_context(chat_params)

#     result = rag_flow.answer_stream(
#         chat_params=chat_params, contextual_messages=contextual_messages, results=results, earlier_thoughts=thoughts
#     )
#     return StreamingResponse(content=format_as_ndjson(result), media_type="application/x-ndjson")


from fastapi.responses import StreamingResponse


@router.post("/chat/stream")
async def chat_stream_handler(
    context: CommonDeps,
    database_session: DBSession,
    openai_embed: EmbeddingsClient,
    openai_chat: ChatClient,
    chat_request: ChatRequest,
):
    import os

    from dotenv import load_dotenv

    # Load environment variables from the .env file located four levels above the current file
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../../.env"))

    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")  # Defaulting to 5432 if not set
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    print("POSTGRES_HOST: ", POSTGRES_HOST)
    print("POSTGRES_USERNAME: ", POSTGRES_USERNAME)
    print("POSTGRES_PASSWORD: ", POSTGRES_PASSWORD)
    print("POSTGRES_DATABASE: ", POSTGRES_DATABASE)
    print("POSTGRES_PORT: ", POSTGRES_PORT)
    try:
        print(database_session)
        print(context)
        print("c: ", chat_request)

        conn_params = {
            "dbname": POSTGRES_DATABASE,
            "user": POSTGRES_USERNAME,
            "password": POSTGRES_PASSWORD,
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
        }

        question = chat_request.messages[-1]["content"]
        print("q: ", question)
        openai.api_type = "azure"
        openai.api_base = AZURE_OPENAI_ENDPOINT
        openai.api_key = AZURE_OPENAI_KEY
        openai.api_version = "2023-05-15"

        def create_embeddings(query):
            try:
                response = openai.embeddings.create(input=query, model=context.openai_embed_deployment)
                embedding = response.data[0].embedding
                return np.array(embedding)
            except Exception as exc:
                return {"error": f"Error generating embeddings: {exc}"}

        embedding = create_embeddings(question)
        print("e: ", embedding)
        if isinstance(embedding, dict) and "error" in embedding:

            async def error_stream():
                yield json.dumps(embedding)

            return StreamingResponse(error_stream(), media_type="text/event-stream")

        # # Execute SQL function to rank results based on embeddings
        # def execute_rerank_function(embedding, query, top_n, consider_n):
        #     try:
        #         print("executing rerank function call")
        #         with psycopg2.connect(**conn_params) as conn:
        #             with conn.cursor() as cursor:
        #                 cursor.execute(
        #                     """
        #                     SELECT * FROM get_vector_rerank_pagerank_rrf2_cases(%s, %s, %s, %s);
        #                     """,
        #                     (embedding, query, top_n, consider_n),
        #                 )
        #                 print("executed rerank function call")
        #                 results = cursor.fetchall()
        #                 print("results: ", results)
        #                 colnames = [desc[0] for desc in cursor.description]
        #                 return pd.DataFrame(results, columns=colnames)
        #     except psycopg2.Error as exc:
        #         return {"error": f"Error executing SQL function: {exc}"}

        # print("rerank function call")
        # results_df = execute_rerank_function(embedding, question, top_n=5, consider_n=10)
        import json

        from sqlalchemy import text

        def convert_embedding_to_vector(embedding):
            """Convert a numpy array to a PostgreSQL-compatible VECTOR string format."""
            vector_str = ",".join(map(str, embedding))
            # Directly format as '[x1, x2, ...]' without type annotation
            return f"[{vector_str}]"

        async def execute_rerank_function(database_session, embedding, query, top_n, consider_n):
            try:
                print("Executing rerank function call")

                # Convert the embedding to a format PostgreSQL understands
                embedding_str = convert_embedding_to_vector(embedding)

                # Prepare the SQL function call with parameters
                sql_query = """
                SELECT * FROM get_vector_rerank_pagerank_rrf2_cases(:embedding, :query, :top_n, :consider_n)
                """

                # Execute the query using SQLAlchemy's AsyncSession
                result = await database_session.execute(
                    text(sql_query),
                    {
                        "embedding": embedding_str,  # Directly pass the formatted string
                        "query": query,
                        "top_n": top_n,
                        "consider_n": consider_n,
                    },
                )

                print("Executed rerank function call")

                # Fetch results and column names
                results = result.fetchall()
                colnames = result.keys()

                # Convert results to a DataFrame
                return pd.DataFrame(results, columns=colnames)

            except Exception as exc:
                print(f"Error executing SQL function: {exc}")
                return {"error": f"Error executing SQL function: {exc}"}

        # Call your updated function with `database_session`
        results_df = await execute_rerank_function(
            database_session=database_session, embedding=embedding, query=question, top_n=5, consider_n=10
        )

        print("results_df: ", results_df)

        if isinstance(results_df, dict) and "error" in results_df:

            async def error_stream():
                yield json.dumps(results_df)

            return StreamingResponse(error_stream(), media_type="text/event-stream")

        if results_df.empty:

            async def no_results_stream():
                yield json.dumps({"error": "No relevant cases found"})

            return StreamingResponse(no_results_stream(), media_type="text/event-stream")

        # Generate legal insights using OpenAI Chat
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
        )

        # def generate_legal_response(question, context):
        #     completion = client.chat.completions.create(
        #         model="gpt-4o",
        #         messages=[
        #             {
        #                 "role": "system",
        #                 "content": """You are a Legal Research AI Assistant that helps people understand relevant legal cases. Answer the user's QUESTION below using provided cases in the CONTEXT section. Keep your answer grounded in the cases in the CONTEXT section. If the CONTEXT section doesn’t contain the facts to answer the QUESTION, return NONE. Identify top 2 legal principles used in the cases provided, explain them and group prominent cases by those principles.""",
        #             },
        #             {"role": "user", "content": f"QUESTION: {question}\nCONTEXT: {context}"},
        #         ],
        #         max_tokens=800,
        #         temperature=0.3,
        #         frequency_penalty=0,
        #         presence_penalty=0,
        #         stop=None,
        #         stream=True,  # Enable streaming responses
        #     )
        #     return completion
        from fastapi.responses import StreamingResponse

        def generate_legal_response(question, context):
            client = AzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_KEY, api_version=openai.api_version
            )
            # {"role": "user", "content": f"QUESTION: {question}\nCONTEXT: {context}"},
            # "content": """You are a Legal Research AI Assistant that helps people understand relevant legal cases. Answer the user's QUESTION below using provided cases in the CONTEXT section. Keep your answer grounded in the cases in the CONTEXT section. If the CONTEXT section doesn’t contain the facts to answer the QUESTION, return NONE. Identify top 2 legal principles used in the cases provided, explain them and group prominent cases by those principles.""",
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a Legal Research AI Assistant that helps people""",
                    },
                    {"role": "user", "content": "What is the weather today?"},
                ],
                max_tokens=800,
                temperature=0.3,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=False,
            )
            print("OpenAI Response:", response)  # Debugging print statement
            return response

        import asyncio

        async def stream_response_generator(stream_response):
            try:
                # Iterate over the synchronous stream response
                for chunk in stream_response:
                    print("Full Chunk received:", chunk)  # Debugging print statement
                    print("Chunk Type:", type(chunk))  # Print the type of chunk for understanding

                    # Check if the first element of the tuple is 'choices'
                    if isinstance(chunk, tuple) and chunk[0] == "choices":
                        choices = chunk[1]  # Get the list of choices

                        for choice in choices:
                            # Check if the 'message' key and 'content' exist in this choice
                            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                                message_content = choice.message.content
                                print(f"Extracted message content: {message_content}")
                                if message_content:
                                    # Yield the message content as a JSON string
                                    yield json.dumps({"content": message_content})
                                    # yield f"data: {json.dumps({'content': message_content})}\n\n"

                    await asyncio.sleep(0)  # Yield control to the event loop

            except Exception as exc:
                print(f"Error in stream_response_generator: {exc}")
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        # Convert the results DataFrame to JSON format for context
        context_json = results_df.to_json(orient="records")
        stream_response = generate_legal_response(question, context_json)

        # Step 4: Return a streaming response using FastAPI's StreamingResponse
        return StreamingResponse(stream_response_generator(stream_response), media_type="text/event-stream")

        # async def stream():
        #     async for message in stream_response:
        #         yield f"data: {json.dumps(message)}\n\n"

        # return StreamingResponse(stream(), media_type="text/event-stream")

    except Exception as exc:

        async def error_stream(exc=exc):
            yield json.dumps({"error": f"Unhandled error: {str(exc)}"})

        return StreamingResponse(error_stream(), media_type="text/event-stream")
