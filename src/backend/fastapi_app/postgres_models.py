from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Define the models
class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column()
    brand: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    price: Mapped[float] = mapped_column()
    # Embeddings for different models:
    embedding_ada002: Mapped[Vector] = mapped_column(Vector(1536), nullable=True)  # ada-002
    embedding_nomic: Mapped[Vector] = mapped_column(Vector(768), nullable=True)  # nomic-embed-text

    def to_dict(self, include_embedding: bool = False):
        model_dict = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        if include_embedding:
            model_dict["embedding_ada002"] = model_dict.get("embedding_ada002", [])
            model_dict["embedding_nomic"] = model_dict.get("embedding_nomic", [])
        else:
            del model_dict["embedding_ada002"]
            del model_dict["embedding_nomic"]
        return model_dict

    def to_str_for_rag(self):
        return f"Name:{self.name} Description:{self.description} Price:{self.price} Brand:{self.brand} Type:{self.type}"

    def to_str_for_embedding(self):
        return f"Name: {self.name} Description: {self.description} Type: {self.type}"


# class Case(Base):
#     __tablename__ = "cases"
#     id: Mapped[str] = mapped_column(Text, primary_key=True)
#     data: Mapped[MutableDict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False)
#     description_vector: Mapped[Vector] = mapped_column(
#         Vector(1536), nullable=True
#     )  # Assuming 1536-dimensional vector for description

#     def to_dict(self, include_vector: bool = False):
#         """
#         Converts the Case instance to a dictionary representation.
#         """
#         model_dict = {column.name: getattr(self, column.name) for column in self.__table__.columns}
#         if include_vector:
#             model_dict["description_vector"] = model_dict.get("description_vector", [])
#         else:
#             del model_dict["description_vector"]
#         return model_dict

#     def to_str_for_rag(self):
#         """
#         Converts Case to a string representation for Retrieval-Augmented Generation (RAG) usage.
#         """
#         data_fields = " ".join([f"{key}:{value}" for key, value in self.data.items()])
#         return f"ID: {self.id} Data: {data_fields}"

#     def to_str_for_embedding(self):
#         """
#         Converts Case to a string representation for embeddings.
#         """
#         return " ".join([f"{key}: {value}" for key, value in self.data.items() if key != "embedding"])


class Case(Base):
    __tablename__ = "cases_updated"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    data: Mapped[MutableDict] = mapped_column(MutableDict.as_mutable(JSONB), nullable=False)
    description_vector: Mapped[Vector] = mapped_column(Vector(1536), nullable=True)

    def to_dict(self, include_vectors: bool = False):
        """
        Converts the Case instance to a dictionary representation.
        """
        model_dict = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        if not include_vectors:
            model_dict.pop("description_vector", None)
        return model_dict

    def to_str_for_rag(self):
        """
        Converts Case to a string representation for Retrieval-Augmented Generation (RAG) usage.
        """
        data_fields = " ".join([f"{key}:{value}" for key, value in self.data.items()])
        return f"ID: {self.id} Data: {data_fields}"

    def to_str_for_embedding(self):
        """
        Converts Case to a string representation for embeddings.
        """
        return " ".join([f"{key}: {value}" for key, value in self.data.items() if key != "embedding"])


# Define HNSW index to support vector similarity search
# Use the vector_ip_ops access method (inner product) since these embeddings are normalized

# table_name = Item.__tablename__

# index_ada002 = Index(
#     "hnsw_index_for_innerproduct_{table_name}_embedding_ada002",
#     Item.embedding_ada002,
#     postgresql_using="hnsw",
#     postgresql_with={"m": 16, "ef_construction": 64},
#     postgresql_ops={"embedding_ada002": "vector_ip_ops"},
# )

# index_nomic = Index(
#     f"hnsw_index_for_innerproduct_{table_name}_embedding_nomic",
#     Item.embedding_nomic,
#     postgresql_using="hnsw",
#     postgresql_with={"m": 16, "ef_construction": 64},
#     postgresql_ops={"embedding_nomic": "vector_ip_ops"},
# )

table_name = Case.__tablename__

index_description_vector = Index(
    f"{table_name}_description_vector_idx",
    Case.description_vector,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"description_vector": "vector_cosine_ops"},
)
