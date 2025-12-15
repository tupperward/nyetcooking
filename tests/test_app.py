import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.app import (
    app,
    get_recipe_slug,
    extract_nyt_recipe_id,
    recipe_to_markdown,
    cache_recipe,
    get_cached_recipe,
    get_cache_keys,
    get_recipe_with_retry,
    connect_to_redis_with_retry
)


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_recipe():
    """Sample recipe data for testing"""
    return {
        '@type': 'Recipe',
        'name': 'Test Recipe',
        'description': 'A delicious test recipe',
        'author': {'name': 'Test Chef'},
        'image': 'https://example.com/image.jpg',
        'recipeIngredient': ['1 cup flour', '2 eggs', '1 cup milk'],
        'recipeInstructions': [
            {'@type': 'HowToStep', 'text': 'Mix ingredients'},
            {'@type': 'HowToStep', 'text': 'Bake at 350F'}
        ],
        'prepTime': 'PT15M',
        'cookTime': 'PT30M',
        'totalTime': 'PT45M',
        'recipeYield': '4 servings',
        'aggregateRating': {
            'ratingValue': 4.5,
            'reviewCount': 100
        }
    }


@pytest.fixture
def sample_recipe_with_image_object():
    """Sample recipe with ImageObject format"""
    return {
        '@type': 'Recipe',
        'name': 'Test Recipe with Image Object',
        'image': {
            '@type': 'ImageObject',
            'url': 'https://example.com/image.jpg'
        },
        'recipeIngredient': ['1 cup flour'],
        'recipeInstructions': [{'text': 'Mix it up'}]
    }


class TestRecipeSlug:
    """Test recipe slug generation"""

    def test_basic_slug(self):
        recipe = {'name': 'Chocolate Chip Cookies'}
        slug = get_recipe_slug(recipe)
        assert slug == 'chocolate-chip-cookies'

    def test_slug_with_special_chars(self):
        recipe = {'name': "Mom's Best Pie!"}
        slug = get_recipe_slug(recipe)
        assert slug == 'moms-best-pie'

    def test_slug_with_nyt_url(self):
        recipe = {'name': 'Banana Bread'}
        url = 'https://cooking.nytimes.com/recipes/1234567-banana-bread'
        slug = get_recipe_slug(recipe, url)
        assert slug == '1234567-banana-bread'

    def test_slug_multiple_spaces(self):
        recipe = {'name': 'Super    Delicious    Cake'}
        slug = get_recipe_slug(recipe)
        assert slug == 'super-delicious-cake'


class TestNYTRecipeID:
    """Test NYT recipe ID extraction"""

    def test_extract_nyt_id(self):
        url = 'https://cooking.nytimes.com/recipes/1234567-recipe-name'
        recipe_id = extract_nyt_recipe_id(url)
        assert recipe_id == '1234567'

    def test_extract_nyt_id_no_match(self):
        url = 'https://example.com/recipes/banana-bread'
        recipe_id = extract_nyt_recipe_id(url)
        assert recipe_id is None

    def test_extract_nyt_id_guides_no_match(self):
        # Function only matches /recipes/, not /guides/
        url = 'https://cooking.nytimes.com/guides/1234-guide'
        recipe_id = extract_nyt_recipe_id(url)
        assert recipe_id is None


class TestMarkdownConversion:
    """Test recipe to markdown conversion"""

    def test_basic_markdown(self, sample_recipe):
        md = recipe_to_markdown(sample_recipe)
        assert '# Test Recipe' in md
        assert 'By Test Chef' in md
        assert '## Ingredients' in md
        assert '1 cup flour' in md
        assert '## Instructions' in md
        assert 'Mix ingredients' in md

    def test_markdown_with_times(self, sample_recipe):
        md = recipe_to_markdown(sample_recipe)
        assert 'Total Time:' in md
        assert 'Prep Time:' in md
        assert 'Cook Time:' in md

    def test_markdown_with_rating(self, sample_recipe):
        md = recipe_to_markdown(sample_recipe)
        assert 'Rating:' in md
        assert '4.5/5' in md

    def test_markdown_with_tips(self, sample_recipe):
        sample_recipe['tips'] = ['Tip 1', 'Tip 2']
        md = recipe_to_markdown(sample_recipe)
        assert '## Tips' in md
        assert 'Tip 1' in md


class TestCaching:
    """Test recipe caching functions"""

    def test_cache_and_retrieve(self, sample_recipe):
        slug = 'test-recipe'
        url = 'https://example.com/test'

        # Cache the recipe
        cache_recipe(slug, sample_recipe, url)

        # Retrieve it
        cached = get_cached_recipe(slug)
        assert cached is not None
        assert cached['recipe']['name'] == 'Test Recipe'
        assert cached['original_url'] == url

    def test_cache_keys(self, sample_recipe):
        slug = 'test-cache-keys'
        cache_recipe(slug, sample_recipe, 'https://example.com')

        keys = get_cache_keys()
        assert slug in keys

    def test_get_nonexistent_recipe(self):
        cached = get_cached_recipe('nonexistent-slug')
        assert cached is None


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'cache_backend' in data


class TestIndexRoute:
    """Test main index route"""

    def test_index_with_slash(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'Nyetcooking' in response.data


class TestRecipeProcessing:
    """Test recipe processing endpoint"""

    @patch('web.app.get_recipe_with_retry')
    def test_process_recipe_success(self, mock_get_recipe, client, sample_recipe):
        mock_get_recipe.return_value = sample_recipe

        response = client.post('/process', data={
            'recipe_url': 'https://example.com/recipe'
        }, follow_redirects=False)

        assert response.status_code == 302  # Redirect
        # Should redirect to clean path
        assert response.location == '/example.com/recipe'

    def test_process_recipe_no_url(self, client):
        response = client.post('/process', data={})
        assert response.status_code == 302  # Redirect to index

    @patch('web.app.get_recipe_with_retry')
    def test_process_recipe_failure(self, mock_get_recipe, client):
        mock_get_recipe.side_effect = ValueError("Failed to fetch")

        response = client.post('/process', data={
            'recipe_url': 'https://example.com/bad-recipe'
        })

        assert response.status_code == 400


class TestRetryLogic:
    """Test retry functionality"""

    @patch('web.app.get_recipe')
    @patch('web.app.time.sleep')  # Mock sleep to speed up tests
    def test_retry_success_on_first_attempt(self, mock_sleep, mock_get_recipe, sample_recipe):
        mock_get_recipe.return_value = sample_recipe

        result = get_recipe_with_retry('https://example.com/recipe')

        assert result == sample_recipe
        assert mock_get_recipe.call_count == 1
        assert mock_sleep.call_count == 0

    @patch('web.app.get_recipe')
    @patch('web.app.time.sleep')
    def test_retry_success_on_second_attempt(self, mock_sleep, mock_get_recipe, sample_recipe):
        mock_get_recipe.side_effect = [
            ValueError("First attempt failed"),
            sample_recipe
        ]

        result = get_recipe_with_retry('https://example.com/recipe', max_retries=3)

        assert result == sample_recipe
        assert mock_get_recipe.call_count == 2
        assert mock_sleep.call_count == 1

    @patch('web.app.get_recipe')
    @patch('web.app.time.sleep')
    def test_retry_all_attempts_fail(self, mock_sleep, mock_get_recipe):
        mock_get_recipe.side_effect = ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            get_recipe_with_retry('https://example.com/recipe', max_retries=3)

        assert mock_get_recipe.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between attempts, not after last


class TestImageFormats:
    """Test different image format handling"""

    def test_recipe_with_string_image(self, client):
        recipe = {
            'name': 'Test',
            'image': 'https://example.com/image.jpg',
            'recipeIngredient': ['flour'],
            'recipeInstructions': [{'text': 'mix'}]
        }
        cache_recipe('string-image-test', recipe, 'https://example.com')

        response = client.get('/string-image-test')
        assert response.status_code == 200
        assert b'https://example.com/image.jpg' in response.data

    def test_recipe_with_image_object(self, client, sample_recipe_with_image_object):
        cache_recipe('object-image-test', sample_recipe_with_image_object, 'https://example.com')

        response = client.get('/object-image-test')
        assert response.status_code == 200
        # Check that og:image meta tag is present
        assert b'og:image' in response.data

    def test_recipe_with_image_array(self, client):
        recipe = {
            'name': 'Test',
            'image': ['https://example.com/image1.jpg', 'https://example.com/image2.jpg'],
            'recipeIngredient': ['flour'],
            'recipeInstructions': [{'text': 'mix'}]
        }
        cache_recipe('array-image-test', recipe, 'https://example.com')

        response = client.get('/array-image-test')
        assert response.status_code == 200
        # Should use first image
        assert b'https://example.com/image1.jpg' in response.data


class TestMarkdownExport:
    """Test markdown export endpoint"""

    def test_markdown_export(self, client, sample_recipe):
        cache_recipe('example.com/recipe', sample_recipe, 'https://example.com/recipe')

        response = client.get('/example.com/recipe/markdown')
        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
        assert b'# Test Recipe' in response.data

    @patch('web.app.get_recipe_with_retry')
    def test_markdown_export_not_cached(self, mock_get_recipe, client, sample_recipe):
        """Test markdown export fetches recipe if not cached"""
        from web.app import recipe_cache
        recipe_cache.clear()  # Clear in-memory cache

        mock_get_recipe.return_value = sample_recipe

        response = client.get('/example.com/recipe/markdown')

        assert response.status_code == 200
        assert mock_get_recipe.called
        assert b'# Test Recipe' in response.data


class TestPathBasedRouting:
    """Test new path-based URL routing"""

    @patch('web.app.get_recipe_with_retry')
    def test_path_based_url_cached(self, mock_get_recipe, client, sample_recipe):
        """Test accessing recipe by path when cached"""
        # Pre-cache the recipe
        cache_recipe('babi.sh/recipes/test-recipe', sample_recipe, 'https://babi.sh/recipes/test-recipe')

        response = client.get('/babi.sh/recipes/test-recipe')

        assert response.status_code == 200
        assert b'Test Recipe' in response.data
        # Should not fetch since it's cached
        mock_get_recipe.assert_not_called()

    @patch('web.app.get_recipe_with_retry')
    def test_path_based_url_not_cached(self, mock_get_recipe, client, sample_recipe):
        """Test accessing recipe by path when not cached - should auto-fetch"""
        from web.app import recipe_cache
        recipe_cache.clear()  # Clear in-memory cache

        mock_get_recipe.return_value = sample_recipe

        response = client.get('/example.com/recipe')

        assert response.status_code == 200
        assert b'Test Recipe' in response.data
        # Should attempt to fetch
        assert mock_get_recipe.called
        # Should try https://example.com/recipe
        called_url = mock_get_recipe.call_args_list[0][0][0]
        assert 'example.com/recipe' in called_url

    @patch('web.app.get_recipe_with_retry')
    def test_path_based_url_fetch_failure(self, mock_get_recipe, client):
        """Test 404 when fetch fails"""
        mock_get_recipe.side_effect = ValueError("Not found")

        response = client.get('/nonexistent.com/recipe')

        assert response.status_code == 404


class TestProcessEndpoint:
    """Test recipe processing with new URL format"""

    @patch('web.app.get_recipe_with_retry')
    def test_process_redirects_to_clean_path(self, mock_get_recipe, client, sample_recipe):
        """Test that /process redirects to clean path format"""
        mock_get_recipe.return_value = sample_recipe

        response = client.post('/process', data={
            'recipe_url': 'https://www.babi.sh/recipes/test-recipe'
        }, follow_redirects=False)

        assert response.status_code == 302
        # Should redirect to clean path (no https://, no www.)
        assert response.location == '/babi.sh/recipes/test-recipe'


class TestRedisRetry:
    """Test Redis connection retry logic"""

    @patch('web.app.time.sleep')
    @patch.dict(os.environ, {'REDIS_HOST': 'test-redis', 'REDIS_PORT': '6379'})
    def test_redis_connection_success_first_attempt(self, mock_sleep):
        """Test successful Redis connection on first attempt"""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance

            client, success = connect_to_redis_with_retry(max_retries=3)

            assert success is True
            assert client == mock_redis_instance
            mock_redis_instance.ping.assert_called_once()
            mock_sleep.assert_not_called()

    @patch('web.app.time.sleep')
    @patch.dict(os.environ, {'REDIS_HOST': 'test-redis', 'REDIS_PORT': '6379'})
    def test_redis_connection_retry_then_success(self, mock_sleep):
        """Test Redis connection succeeds after retry"""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_instance = MagicMock()
            # Fail twice, then succeed
            mock_redis_instance.ping.side_effect = [
                Exception("Connection refused"),
                Exception("Connection refused"),
                True
            ]
            mock_redis_class.return_value = mock_redis_instance

            client, success = connect_to_redis_with_retry(max_retries=5)

            assert success is True
            assert client == mock_redis_instance
            assert mock_redis_instance.ping.call_count == 3
            # Should sleep twice (after 1st and 2nd failures)
            assert mock_sleep.call_count == 2
            # Check exponential backoff: 1s, 2s
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)

    @patch('web.app.time.sleep')
    @patch.dict(os.environ, {'REDIS_HOST': 'test-redis', 'REDIS_PORT': '6379'})
    def test_redis_connection_all_retries_fail(self, mock_sleep):
        """Test Redis connection fails after all retries"""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.side_effect = Exception("Connection refused")
            mock_redis_class.return_value = mock_redis_instance

            client, success = connect_to_redis_with_retry(max_retries=3)

            assert success is False
            assert client is None
            assert mock_redis_instance.ping.call_count == 3
            # Should sleep twice (after 1st and 2nd failures, not after last)
            assert mock_sleep.call_count == 2

    def test_redis_connection_module_not_available(self):
        """Test handling when redis module is not available"""
        with patch.dict('sys.modules', {'redis': None}):
            with patch('web.app.logger') as mock_logger:
                # This will cause ImportError
                client, success = connect_to_redis_with_retry(max_retries=1)

                assert success is False
                assert client is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
