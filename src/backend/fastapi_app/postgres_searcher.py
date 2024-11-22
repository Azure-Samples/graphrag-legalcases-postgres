import logging
import subprocess
from pathlib import Path

from openai import AsyncAzureOpenAI, AsyncOpenAI
from pgvector.utils import to_db
from sqlalchemy import String, column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_app.api_models import RetrievalMode
from fastapi_app.embeddings import compute_text_embedding
from fastapi_app.postgres_models import Case

logger = logging.getLogger("legalcaseapp")


class PostgresSearcher:
    def __init__(
        self,
        db_session: AsyncSession,
        openai_embed_client: AsyncOpenAI | AsyncAzureOpenAI,
        embed_deployment: str | None,  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embed_model: str,
        embed_dimensions: int | None,
        embedding_column: str,
    ):
        self.db_session = db_session
        self.openai_embed_client = openai_embed_client
        self.embed_model = embed_model
        self.embed_deployment = embed_deployment
        self.embed_dimensions = embed_dimensions
        self.embedding_column = embedding_column

    def build_filter_clause(self, filters) -> tuple[str, str]:
        if filters is None:
            return "", ""
        filter_clauses = []
        for filter in filters:
            if isinstance(filter["value"], str):
                filter["value"] = f"'{filter['value']}'"
            filter_clauses.append(f"{filter['column']} {filter['comparison_operator']} {filter['value']}")
        filter_clause = " AND ".join(filter_clauses)
        if len(filter_clause) > 0:
            return f"WHERE {filter_clause}", f"AND {filter_clause}"
        return "", ""

    async def search(
        self,
        query_text: str | None,
        query_vector: list[float] | list,
        top: int = 5,
        filters: list[dict] | None = None,
        retrieval_mode: RetrievalMode = RetrievalMode.GRAPHRAG,
    ):
        # Build filters if provided (assuming self.build_filter_clause exists and returns correct clauses)
        filter_clause_where, filter_clause_and = self.build_filter_clause(filters)
        table_name = Case.__tablename__

        token_file = Path(__file__).parent / "postgres_token.txt"

        if token_file.exists() and retrieval_mode == RetrievalMode.GRAPHRAG:
            try:
                script_path = Path(__file__).parent / "setup_postgres_age.py"

                if not script_path.exists():
                    logger.error(f"Setup script not found at {script_path}")
                    raise FileNotFoundError(f"Script {script_path} does not exist.")

                logger.info("Running setup_postgres_age.py...")
                subprocess.run(["python", str(script_path)], check=True)
                logger.info("setup_postgres_age.py completed successfully.")

            except subprocess.CalledProcessError as e:
                logger.error(f"Error occurred while running setup_postgres_age.py: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

        await self.db_session.execute(text('SET search_path = ag_catalog, "$user", public;'))

        if retrieval_mode == RetrievalMode.GRAPHRAG:
            function_call = """
                SELECT * FROM get_vector_semantic_graphrag_cases(
                    :query_text, 
                    CAST(:embedding AS vector(1536)), 
                    :top_n, 
                    :consider_n
                );
            """
        elif retrieval_mode == RetrievalMode.SEMANTIC:
            function_call = """
                SELECT * FROM get_vector_semantic_cases(
                    :query_text, 
                    CAST(:embedding AS vector(1536)), 
                    :top_n, 
                    :consider_n
                );
            """
        elif retrieval_mode == RetrievalMode.VECTOR:
            function_call = """
                SELECT * FROM get_vector_cases(
                    :query_text, 
                    CAST(:embedding AS vector(1536)), 
                    :top_n
                );
            """
        else:
            raise ValueError("Invalid retrieval_mode. Options are: VECTOR, SEMANTIC, GRAPHRAG")

        sql = text(function_call).columns(
            column("rrf.id", String),
        )

        # Execute the query with the required parameters
        await self.db_session.execute(text('SET search_path = ag_catalog, "$user", public;'))

        results = (
            await self.db_session.execute(
                sql,
                {
                    "embedding": to_db(query_vector),
                    "top_n": top,
                    "consider_n": 60,
                    "query_text": "Water leaking into the apartment from the floor above.",
                },
            )
        ).fetchall()

        if not results:
            return []  # Return an empty list if no results are found

        # Convert results to SQLAlchemy models
        row_models = []
        for row in results[:top]:
            id = row.id  # Adjust if column names differ
            # Fetch the corresponding row using the ID
            item = await self.db_session.execute(select(Case).where(Case.id == id))
            row_models.append(item.scalar())
        return row_models

    async def search_and_embed(
        self,
        retrieval_mode: RetrievalMode,
        query_text: str | None = None,
        top: int = 5,
        enable_vector_search: bool = False,
        enable_text_search: bool = False,
        filters: list[dict] | None = None,
    ) -> list[Case]:
        """
        Search rows by query text. Optionally converts the query text to a vector if enable_vector_search is True.
        """
        vector: list[float] = []
        # if enable_vector_search and query_text is not None:
        vector = await compute_text_embedding(
            query_text,
            self.openai_embed_client,
            self.embed_model,
            self.embed_deployment,
            self.embed_dimensions,
        )
        if not enable_text_search:
            query_text = None

        return await self.search(query_text, vector, top, filters, retrieval_mode)
