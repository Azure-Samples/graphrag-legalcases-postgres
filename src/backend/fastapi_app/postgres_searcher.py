import logging

from openai import AsyncAzureOpenAI, AsyncOpenAI
from pgvector.utils import to_db
from sqlalchemy import String, column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

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

    # async def search(
    #     self, query_text: str | None, query_vector: list[float] | list, top: int = 5, filters: list[dict] | None = None
    # ):
    #     print("Searching")
    #     print(query_text)
    #     filter_clause_where, filter_clause_and = self.build_filter_clause(filters)
    #     table_name = Case.__tablename__
    #     vector_query = f"""
    #         SELECT id, RANK () OVER (ORDER BY {self.embedding_column} <=> :embedding) AS rank
    #             FROM {table_name}
    #             {filter_clause_where}
    #             ORDER BY {self.embedding_column} <=> :embedding
    #             LIMIT 20
    #         """
    #     print("Vector Query", vector_query)

    #     fulltext_query = f"""
    #         SELECT id, RANK () OVER (ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC)
    #             FROM {table_name}, plainto_tsquery('english', :query) query
    #             WHERE to_tsvector('english', description) @@ query {filter_clause_and}
    #             ORDER BY ts_rank_cd(to_tsvector('english', description), query) DESC
    #             LIMIT 20
    #         """

    #     hybrid_query = f"""
    #     WITH vector_search AS (
    #         {vector_query}
    #     ),
    #     fulltext_search AS (
    #         {fulltext_query}
    #     )
    #     SELECT
    #         COALESCE(vector_search.id, fulltext_search.id) AS id,
    #         COALESCE(1.0 / (:k + vector_search.rank), 0.0) +
    #         COALESCE(1.0 / (:k + fulltext_search.rank), 0.0) AS score
    #     FROM vector_search
    #     FULL OUTER JOIN fulltext_search ON vector_search.id = fulltext_search.id
    #     ORDER BY score DESC
    #     LIMIT 20
    #     """

    #     if query_text is not None and len(query_vector) > 0:
    #         sql = text(hybrid_query).columns(column("id", Integer), column("score", Float))
    #     elif len(query_vector) > 0:
    #         sql = text(vector_query).columns(column("id", Integer), column("rank", Integer))
    #     elif query_text is not None:
    #         sql = text(fulltext_query).columns(column("id", Integer), column("rank", Integer))
    #     else:
    #         raise ValueError("Both query text and query vector are empty")

    #     results = (
    #         await self.db_session.execute(
    #             sql,
    #             {"embedding": to_db(query_vector), "query": query_text, "k": 60},
    #         )
    #     ).fetchall()

    #     # Convert results to SQLAlchemy models
    #     row_models = []
    #     for id, _ in results[:top]:
    #         item = await self.db_session.execute(select(Case).where(Case.id == id))
    #         row_models.append(item.scalar())
    #     return row_models

    # async def search(
    #     self, query_text: str | None, query_vector: list[float] | list, top: int = 5, filters: list[dict] | None = None
    # ):
    #     print("Searching")
    #     print(query_text)

    #     # Build filters if provided (assuming self.build_filter_clause exists and returns correct clauses)
    #     filter_clause_where, _ = self.build_filter_clause(filters)
    #     print("Filter clause where", filter_clause_where)
    #     table_name = Case.__tablename__

    #     hybrid_query = f"""
    #     WITH vector_search AS (
    #         SELECT
    #             id,
    #             RANK() OVER (ORDER BY {self.embedding_column} <=> :embedding) AS vector_rank,
    #             data ->> 'name_abbreviation' AS abbr,
    #             (data#>>'{{analysis, pagerank, percentile}}')::NUMERIC AS pagerank,
    #             data
    #         FROM
    #             {table_name}
    #         ORDER BY
    #             {self.embedding_column} <=> :embedding
    #         LIMIT
    #             :consider_n
    #     ),
    #     graph_ranked AS (
    #         SELECT
    #             RANK() OVER (ORDER BY vector_search.pagerank DESC) AS pagerank_rank,
    #             0.0::DOUBLE PRECISION AS relevance,  -- Placeholder for relevance
    #             vector_search.*
    #         FROM
    #             vector_search
    #         ORDER BY
    #             vector_search.pagerank DESC
    #     ),
    #     rrf AS (
    #         SELECT
    #             COALESCE(1.0 / (60 + graph_ranked.pagerank_rank), 0.0) +
    #             COALESCE(1.0 / (60 + graph_ranked.vector_rank), 0.0) AS score,
    #             graph_ranked.pagerank_rank,
    #             graph_ranked.relevance,
    #             graph_ranked.id,
    #             graph_ranked.vector_rank,
    #             graph_ranked.abbr,
    #             graph_ranked.pagerank,
    #             graph_ranked.data
    #         FROM
    #             graph_ranked
    #         ORDER BY
    #             score DESC
    #         LIMIT
    #             :top_n
    #     )
    #     SELECT *
    #     FROM rrf;
    #     """

    #     # Create the SQLAlchemy text query
    #     sql = text(hybrid_query).columns(
    #         column("score", Numeric),
    #         column("pagerank_rank", Integer),
    #         column("relevance", Float),
    #         column("id", String),
    #         column("vector_rank", Integer),
    #         column("abbr", String),
    #         column("pagerank", Numeric),
    #         column("data", JSONB),
    #     )

    #     # Execute the query with the required parameters
    #     results = (
    #         await self.db_session.execute(sql, {"embedding": to_db(query_vector), "top_n": top, "consider_n": 60})
    #     ).fetchall()

    #     if not results:
    #         return []  # Return an empty list if no results are found

    #     # Convert results to SQLAlchemy models
    #     row_models = []
    #     for row in results[:top]:
    #         id = row.id  # Adjust if column names differ
    #         # Fetch the corresponding row using the ID
    #         item = await self.db_session.execute(select(Case).where(Case.id == id))
    #         row_models.append(item.scalar())
    #     return row_models

    async def search(
        self, query_text: str | None, query_vector: list[float] | list, top: int = 5, filters: list[dict] | None = None
    ):
        print("Searching")
        print(query_text)
        print("top", top)

        # Build filters if provided (assuming self.build_filter_clause exists and returns correct clauses)
        filter_clause_where, filter_clause_and = self.build_filter_clause(filters)
        table_name = Case.__tablename__

        # Vector-based search query, using similar logic as the older function
        # hybrid_query = """
        #     WITH vector AS (
        #             SELECT cases_summary.id,
        #                 cases_summary.data#>>'{name_abbreviation}' AS case_name,
        #                 cases_summary.data#>>'{decision_date}' AS date,
        #                 cases_summary.data,
        #                 RANK() OVER (ORDER BY description_vector <=> :embedding) AS vector_rank
        #             FROM cases_summary
        #             WHERE (cases_summary.data#>>'{court, id}')::integer IN (9029)
        #             ORDER BY description_vector <=> :embedding
        #             LIMIT :consider_n
        #         ),
        #         json_payload AS (
        #             SELECT jsonb_build_object(
        #                 'pairs',
        #                 jsonb_agg(
        #                     jsonb_build_array(
        #                         :query_text,
        #                         LEFT(vector.data -> 'casebody' -> 'opinions' -> 0 ->> 'text', 800)
        #                     )
        #                 )
        #             ) AS json_pairs
        #             FROM vector
        #         ),
        #         semantic AS (
        #             SELECT elem.relevance::DOUBLE precision AS relevance, elem.ordinality
        #             FROM json_payload AS jp,
        #                 LATERAL jsonb_array_elements(
        #                     azure_ml.invoke(
        #                         jp.json_pairs,
        #                         deployment_name => 'bge-v2-m3-1',
        #                         timeout_ms => 180000
        #                     )
        #                 ) WITH ORDINALITY AS elem(relevance)
        #         ),
        #         semantic_ranked AS (
        #             SELECT RANK() OVER (ORDER BY semantic.relevance DESC) AS semantic_rank,
        #                 semantic.*, vector.*
        #             FROM vector
        #             JOIN semantic ON vector.vector_rank = semantic.ordinality
        #             ORDER BY semantic.relevance DESC
        #         ),
        #         graph_query AS (
        #             SELECT * FROM cypher('case_graph',
        #                 $$ MATCH (s)-[r:CITES]->(n) RETURN n.case_id AS case_id, s.case_id AS ref_id $$
        #             ) AS (case_id TEXT, ref_id TEXT)
        #         ),
        #         graph AS (
        #             SELECT subquery.id, COUNT(ref_id) AS refs
        #             FROM (
        #                 SELECT semantic_ranked.id, graph_query.ref_id, c2.description_vector <=> embedding AS ref_cosine
        #                 FROM semantic_ranked
        #                 LEFT JOIN graph_query
        #                 ON semantic_ranked.id = graph_query.case_id
        #                 LEFT JOIN cases_summary c2
        #                 ON c2.id = graph_query.ref_id
        #                 WHERE semantic_ranked.semantic_rank <= 25
        #                 ORDER BY ref_cosine
        #                 LIMIT 200
        #             ) AS subquery
        #             GROUP BY subquery.id
        #         ),
        #         graph2 AS (
        #             SELECT semantic_ranked.*, graph.refs
        #             FROM semantic_ranked
        #             LEFT JOIN graph ON semantic_ranked.id = graph.id
        #         ),
        #         graph_ranked AS (
        #             SELECT RANK() OVER (ORDER BY COALESCE(graph2.refs, 0) DESC) AS graph_rank, graph2.*
        #             FROM graph2
        #             ORDER BY graph_rank DESC
        #         ),
        #         rrf AS (
        #             SELECT
        #                 gold_dataset.label,
        #                 COALESCE(1.0 / (60 + graph_ranked.graph_rank), 0.0) +
        #                 COALESCE(1.0 / (60 + graph_ranked.semantic_rank), 0.0) AS score,
        #                 graph_ranked.*
        #             FROM graph_ranked
        #             LEFT JOIN gold_dataset ON graph_ranked.id = gold_dataset.gold_id
        #             ORDER BY score DESC
        #         )
        #         SELECT
        #             rrf.label, rrf.score, rrf.graph_rank, rrf.semantic_rank, rrf.vector_rank, rrf.id, rrf.case_name, rrf.date, rrf.data, rrf.refs, rrf.relevance
        #         FROM rrf
        #         ORDER BY semantic_rank
        #         LIMIT :top_n;
        # """

        # print("Hybrid Query", hybrid_query)

        # # Create the SQLAlchemy text query
        # sql = text(hybrid_query).columns(
        #     column("id", String),
        #     # column("vector_score", Float),
        #     # column("pagerank", Numeric),
        #     # column("abbr", String),
        #     # column("data", JSONB),
        # )

        result_user = await self.db_session.execute(text("SELECT current_user;"))
        user = result_user.scalar()  # Get the result as a scalar value

        # Print the user
        print("Current User:", user)

        await self.db_session.execute(text('SET search_path = ag_catalog, "$user", public;'))

        function_call = """
            SELECT * FROM get_vector_pagerank_rrf_cases(
                :query_text, 
                CAST(:embedding AS vector(1536)), 
                :top_n, 
                :consider_n
            );
        """

        print("Function Call:", function_call)

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
        query_text: str | None = None,
        top: int = 5,
        enable_vector_search: bool = False,
        enable_text_search: bool = False,
        filters: list[dict] | None = None,
    ) -> list[Case]:
        """
        Search rows by query text. Optionally converts the query text to a vector if enable_vector_search is True.
        """
        print("Enable Vector Search", enable_vector_search)
        print("Enable Text Search", enable_text_search)
        vector: list[float] = []
        if enable_vector_search and query_text is not None:
            vector = await compute_text_embedding(
                query_text,
                self.openai_embed_client,
                self.embed_model,
                self.embed_deployment,
                self.embed_dimensions,
            )
        if not enable_text_search:
            query_text = None

        return await self.search(query_text, vector, top, filters)
