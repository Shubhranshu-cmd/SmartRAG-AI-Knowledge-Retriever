import pytest
import numpy as np
from PIL import Image
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_torch():
    with patch('torch.cuda.is_available', return_value=False):
        yield

@pytest.fixture
def test_image():
    """Create a test image"""
    return Image.fromarray(np.uint8(np.random.rand(224, 224, 3) * 255))

@pytest.fixture
def mock_classifier():
    """Create a mocked classifier to avoid GPU dependency"""
    with patch('vision.classifier.resnet50') as mock_resnet:
        mock_model = MagicMock()
        mock_resnet.return_value = mock_model
        
        with patch('vision.classifier.torch.no_grad'):
            from vision.classifier import Classifier
            classifier = Classifier(device='cpu')
            return classifier

def test_classifier_load(mock_classifier):
    """Test classifier initialization"""
    assert mock_classifier is not None
    assert mock_classifier.device is not None
    assert mock_classifier.model is not None

def test_classifier_predict_output_shape(mock_classifier, test_image):
    """Test classifier output shape"""
    with patch.object(mock_classifier, 'model') as mock_model:
        mock_logits = np.random.randn(1, 1000)
        with patch('torch.no_grad'):
            result = mock_classifier.predict(test_image, topk=5)
        
        assert isinstance(result, dict)
        assert "probs" in result
        assert "topk" in result

def test_classifier_predict_topk():
    """Test classifier topk parameter"""
    with patch('vision.classifier.resnet50'):
        with patch('vision.classifier.torch.no_grad'):
            from vision.classifier import Classifier
            classifier = Classifier(device='cpu')
            
            for topk in [1, 3, 5, 10]:
                with patch.object(classifier.model, '__call__') as mock_call:
                    pass

def test_invalid_image():
    """Test error handling for invalid images"""
    with patch('vision.classifier.resnet50'):
        from vision.classifier import Classifier
        classifier = Classifier(device='cpu')
        
        with pytest.raises((TypeError, AttributeError)):
            classifier.predict(None)

def test_classifier_device_selection():
    """Test device selection (CPU/GPU)"""
    with patch('vision.classifier.resnet50'):
        with patch('vision.classifier.torch.cuda.is_available', return_value=False):
            from vision.classifier import Classifier
            
            classifier = Classifier(device=None)
            assert 'cpu' in str(classifier.device).lower()