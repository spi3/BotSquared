import pytest
import time
import asyncio
from unittest.mock import Mock, patch
from bot_squared.utils.decorators import rate_limit

@pytest.mark.asyncio
async def test_rate_limit_basic():
    """Test basic rate limiting functionality."""
    mock_func = Mock()
    mock_func.return_value = "success"
    
    # Create a decorated function with 0.1 second rate limit
    decorated_func = rate_limit(mock_func, rate_limit=0.1)
    
    # First call should execute immediately
    start_time = time.time()
    result = await decorated_func()
    first_call_time = time.time() - start_time
    
    assert result == "success"
    assert first_call_time < 0.1  # Should execute quickly
    assert mock_func.call_count == 1
    
    # Second call should be rate limited
    start_time = time.time()
    result = await decorated_func()
    second_call_time = time.time() - start_time
    
    assert result == "success"
    assert second_call_time >= 0.1  # Should wait for rate limit
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_rate_limit_retry():
    """Test rate limit retry functionality."""
    mock_func = Mock()
    mock_func.side_effect = [
        Exception("Rate limit exceeded"),
        "success"
    ]
    
    # Create a decorated function with 0.1 second rate limit
    decorated_func = rate_limit(mock_func, rate_limit=0.1)
    
    # Call should retry after rate limit error
    result = await decorated_func()
    
    assert result == "success"
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_rate_limit_max_retries():
    """Test rate limit max retries functionality."""
    mock_func = Mock()
    mock_func.side_effect = Exception("Rate limit exceeded")
    
    # Create a decorated function with 0.1 second rate limit
    decorated_func = rate_limit(mock_func, rate_limit=0.1)
    
    # Call should fail after max retries
    with pytest.raises(Exception) as exc_info:
        await decorated_func()
    
    assert str(exc_info.value) == "Rate limit exceeded"
    assert mock_func.call_count == 3  # Initial call + 2 retries

@pytest.mark.asyncio
async def test_rate_limit_no_delay():
    """Test rate limit with no delay between calls."""
    mock_func = Mock()
    mock_func.return_value = "success"
    
    # Create a decorated function with 0 second rate limit
    decorated_func = rate_limit(mock_func, rate_limit=0)
    
    # Both calls should execute immediately
    start_time = time.time()
    result1 = await decorated_func()
    result2 = await decorated_func()
    total_time = time.time() - start_time
    
    assert result1 == "success"
    assert result2 == "success"
    assert total_time < 0.1  # Should execute quickly
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_rate_limit_with_args():
    """Test rate limit with function arguments."""
    mock_func = Mock()
    mock_func.return_value = "success"
    
    # Create a decorated function with 0.1 second rate limit
    decorated_func = rate_limit(mock_func, rate_limit=0.1)
    
    # Call with arguments
    result = await decorated_func("arg1", kwarg1="value1")
    
    assert result == "success"
    mock_func.assert_called_once_with("arg1", kwarg1="value1")

@pytest.mark.asyncio
async def test_rate_limit_concurrent_calls():
    """Test rate limit with concurrent calls."""
    mock_func = Mock()
    mock_func.return_value = "success"
    
    # Create a decorated function with 0.1 second rate limit
    decorated_func = rate_limit(mock_func, rate_limit=0.1)
    
    # Make concurrent calls
    start_time = time.time()
    results = await asyncio.gather(
        decorated_func(),
        decorated_func(),
        decorated_func()
    )
    total_time = time.time() - start_time
    
    assert all(r == "success" for r in results)
    assert total_time >= 0.2  # Should wait for rate limit between calls
    assert mock_func.call_count == 3 