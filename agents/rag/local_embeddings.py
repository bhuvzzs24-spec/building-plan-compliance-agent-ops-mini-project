from __future__ import annotations

import hashlib
import math
import re
from typing import Sequence

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class LocalHashEmbeddingFunction(EmbeddingFunction[Documents]):
    """Deterministic, offline hashed word/bigram/trigram embeddings.

    This intentionally avoids a network model download. It is a compact
    baseline for a small domain corpus; retrieval relevance must still be
    measured and reviewed.
    """

    dimension = 384

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for document in input:
            tokens = re.findall(r"[a-z0-9]+", str(document).lower())
            features = tokens[:]
            features.extend(f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1))
            features.extend(
                f"{tokens[i]}_{tokens[i + 1]}_{tokens[i + 2]}"
                for i in range(len(tokens) - 2)
            )
            vector = [0.0] * self.dimension
            for feature in features:
                digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
                number = int.from_bytes(digest, "little")
                index = number % self.dimension
                sign = 1.0 if (number >> 32) & 1 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

    @staticmethod
    def name() -> str:
        return "local_hash_ngrams_v1"

    def get_config(self) -> dict:
        return {"dimension": self.dimension}

    @staticmethod
    def build_from_config(config: dict) -> "LocalHashEmbeddingFunction":
        return LocalHashEmbeddingFunction()
