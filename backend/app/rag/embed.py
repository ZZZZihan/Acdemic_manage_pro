"""Optional neural embedder and cross-encoder.

Importing this module does not import sentence-transformers. Weights download
only when ``embed`` or ``cross_encode`` is called.
"""
import logging
import os

from app.rag.errors import RagUnavailable

logger = logging.getLogger(__name__)

_model = None
_model_name = None
_cross = None
_cross_name = None


def _device():
    return os.environ.get("RAG_DEVICE", "cpu")


def neural_embed(texts, model_name):
    model = _load_encoder(model_name)
    vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    return [list(map(float, row)) for row in vectors]


def cross_encode(query, texts, model_name=None):
    model = _load_cross(model_name or os.environ.get("RAG_RERANK_MODEL", "BAAI/bge-reranker-base"))
    pairs = [(query, text or "") for text in texts]
    scores = model.predict(pairs, show_progress_bar=False)
    return [float(score) for score in scores]


def _load_encoder(model_name):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RagUnavailable("嵌入依赖未安装，检索服务不可用") from exc
    try:
        _model = SentenceTransformer(model_name, device=_device())
        _model_name = model_name
    except Exception as exc:
        raise RagUnavailable("嵌入模型加载失败，检索服务不可用") from exc
    logger.info("embedding model loaded name=%s", model_name)
    return _model


def _load_cross(model_name):
    global _cross, _cross_name
    if _cross is not None and _cross_name == model_name:
        return _cross
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RagUnavailable("重排依赖未安装，检索服务不可用") from exc
    try:
        _cross = CrossEncoder(model_name, device=_device())
        _cross_name = model_name
    except Exception as exc:
        raise RagUnavailable("重排模型加载失败，检索服务不可用") from exc
    logger.info("rerank model loaded name=%s", model_name)
    return _cross


class NeuralEmbedder:
    name = "bge"
    # bge-small-zh-v1.5 retrieval instruction. Passages stay unprefixed.
    QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

    def __init__(self, model_name):
        self.model_name = model_name or "BAAI/bge-small-zh-v1.5"
        self.name = "bge"

    def embed(self, texts):
        return neural_embed(texts, self.model_name)

    def embed_query(self, text):
        return neural_embed([self.QUERY_PREFIX + (text or "")], self.model_name)[0]
