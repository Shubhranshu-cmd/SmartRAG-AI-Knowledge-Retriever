import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np

@pytest.fixture
def temp_index_dir():
    """Create temporary index directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_faiss():
    """Mock FAISS library"""
    mock_faiss_module = MagicMock()
    mock_index = MagicMock()
    mock_faiss_module.IndexFlatL2.return_value = mock_index
    mock_faiss_module.read_index.side_effect = FileNotFoundError()
    return mock_faiss_module

def test_store_creation(tmp_path):
    """Test FAISSStore initialization"""
    with patch('services.faiss_store.Config') as mock_config:
        mock_config.INDEX_DIR = tmp_path
        mock_config.UPLOAD_DIR = tmp_path
        
        try:
            store = FAISSStore(dim=384)
            assert store is not None
        except RuntimeError:
            pytest.skip("FAISS not available in test environment")

def test_store_add_search(tmp_path):
    """Test adding and searching vectors"""
    with patch('services.faiss_store.Config') as mock_config:
        mock_config.INDEX_DIR = tmp_path
        mock_config.UPLOAD_DIR = tmp_path
        
        try:
            store = FAISSStore(dim=384)
            embeddings = np.random.rand(2, 384).astype("float32")
            docs = [
                {"content": "hello", "source": "test", "chunk_id": 0},
                {"content": "world", "source": "test", "chunk_id": 1}
            ]
            store.add(embeddings, docs)
            results = store.search(np.random.rand(384).astype("float32"), k=1)
            assert isinstance(results, list)
        except RuntimeError:
            pytest.skip("FAISS not available in test environment")

def test_store_empty_search(tmp_path):
    """Test search on empty store"""
    with patch('services.faiss_store.Config') as mock_config:
        mock_config.INDEX_DIR = tmp_path
        mock_config.UPLOAD_DIR = tmp_path
        
        try:
            store = FAISSStore(dim=384)
            results = store.search(np.random.rand(384).astype("float32"), k=5)
            assert results == []
        except RuntimeError:
            pytest.skip("FAISS not available in test environment")

def test_hf_response_adapter():
    """Test HuggingFace response adapter"""
    from services.faiss_store import HFResponse, HFResponseChoice, HFResponseMessage
    
    message = HFResponseMessage("test content")
    assert message.content == "test content"
    
    choice = HFResponseChoice("test content")
    assert choice.message.content == "test content"
    
    response = HFResponse("test content")
    assert response.choices[0].message.content == "test content"

def test_hf_client_adapter():
    """Test HuggingFace client adapter initialization"""
    with patch('services.faiss_store.InferenceClient'):
        from services.faiss_store import HFClientAdapter
        
        adapter = HFClientAdapter("model-id")
        assert adapter.model_id == "model-id"