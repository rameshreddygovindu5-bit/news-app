# AI Rephrasing System - Low Level Design

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Structures](#data-structures)
4. [Core Algorithms](#core-algorithms)
5. [API Contracts](#api-contracts)
6. [Error Handling](#error-handling)
7. [Performance Considerations](#performance-considerations)
8. [Security Implementation](#security-implementation)

---

## System Overview

### Purpose
Transform raw scraped news content into premium, reader-friendly articles with bilingual support (English/Telugu) while ensuring originality and proper formatting.

### Key Requirements
- **Originality**: Minimum 70% difference from source content
- **Bilingual Output**: English + Telugu with structured HTML
- **Cost Optimization**: Zero-cost processing for Google News
- **High Availability**: Multiple fallback mechanisms
- **Scalability**: Batch processing with parallel execution

---

## Component Architecture

### 1. AI Service (`ai_service.py`)

```python
class AIService:
    """
    Main orchestrator for AI rephrasing operations.
    Manages provider chain, similarity validation, and fallback logic.
    """
    
    # Provider Priority Chain
    PROVIDERS = [
        "gemini_primary",      # Google Gemini 1.5 Flash
        "gemini_secondary",    # Google Gemini 1.5 Pro  
        "gemini_tertiary",     # Backup Gemini key
        "grok",                # xAI Grok
        "openai",              # GPT-4o-mini
        "ollama",              # Local Llama3.2:1b
        "paraphrase_engine"    # Local zero-cost engine
    ]
```

#### Key Methods:

```python
def process_article(self, title: str, content: str, source_name: str) -> Dict:
    """
    Main entry point for article processing.
    
    Flow:
    1. Detect language and source type
    2. Route to appropriate processing path
    3. Apply similarity validation
    4. Return structured result
    """
    
def _try_cloud_providers(self, prompt: str, best_only: bool = False) -> Optional[str]:
    """
    Sequential provider fallback with timeout handling.
    Returns first successful response or None.
    """
    
def _polish_html_content(self, original: str, rephrased_html: str) -> str:
    """
    Apply lexical chain to text nodes while preserving HTML structure.
    Used for polishing successful cloud AI outputs.
    """
```

### 2. Paraphrase Engine (`fast_engine.py`)

```python
class ParaphraseEngine:
    """
    Zero-dependency local paraphrase engine.
    Singleton pattern for performance optimization.
    """
    
    # Core Components
    SYNONYMS: Dict[str, List[str]]  # 190+ word mappings
    OPENERS: List[str]              # Sentence variations
    
    def paraphrase_to_html(self, title: str, content: str, seed: int) -> Dict[str, str]:
        """
        Full pipeline: title + content paraphrase with HTML formatting.
        
        Steps:
        1. Clean input (strip HTML, normalize whitespace)
        2. Apply word substitution (55% probability)
        3. Restructure sentences (add openers, change order)
        4. Remove duplicates
        5. Build structured HTML output
        """
```

#### Core Algorithms:

```python
def _substitute_words(sentence: str, seed: int) -> str:
    """
    Word substitution with synonym dictionary.
    - Preserves capitalization and punctuation
    - 55% substitution probability
    - Context-aware for news vocabulary
    """
    
def _restructure_sentence(sentence: str, idx: int) -> str:
    """
    Structural variation through:
    - Sentence openers (every 3rd sentence)
    - Clause reordering
    - Passive/active voice flipping
    """
    
def build_html(title: str, plain_content: str) -> str:
    """
    Convert plain text to structured HTML:
    
    Structure:
    <p><strong>Key Summary</strong></p>
    <p><b>Key Highlights:</b></p>
    <ul><li>Point 1</li><li>Point 2</li><li>Point 3</li></ul>
    <p>Background paragraph</p>
    <p>Analysis paragraph</p>
    <p><i>What's Next: ...</i></p>
    """
```

### 3. Task Processor (`celery_app.py`)

```python
@celery_app.task(name="app.tasks.celery_app.process_ai_batch")
def process_ai_batch():
    """
    Batch processing coordinator.
    
    Algorithm:
    1. Reset stuck articles (>5 min in "processing")
    2. Fetch pending articles (random order, batch size limit)
    3. Mark as "processing" (atomic operation)
    4. Parallel processing with ThreadPoolExecutor
    5. Update results and trigger downstream tasks
    """
    
def worker_process_ai(article_id: int) -> bool:
    """
    Individual article processor.
    
    Steps:
    1. Load article from database
    2. Call ai_service.process_article()
    3. Update article fields
    4. Handle exceptions and logging
    """
```

---

## Data Structures

### Database Schema (`models.py`)

```python
class NewsArticle(Base):
    """
    Core article entity with all content variants.
    """
    
    # Original Content
    original_title: Text      # Raw scraped title
    original_content: Text     # Raw scraped content
    original_url: String       # Source URL
    original_language: String  # Detected language
    
    # AI Rephrased Content (English)
    rephrased_title: Text      # AI-generated title
    rephrased_content: Text    # AI-generated HTML content
    
    # AI Rephrased Content (Telugu)
    telugu_title: Text         # Telugu title
    telugu_content: Text       # Telugu HTML content
    
    # Processing Metadata
    ai_status: String          # pending/processing/success/failed
    ai_error_count: Integer    # Retry counter
    flag: String              # N=New, A=Processed, Y=Top News, P=Pending
    similarity_score: Float   # Content similarity to source
    
    # Categorization
    category: String          # News category
    slug: String             # URL-friendly identifier
    tags: JSON               # Tag array
    
    # Performance Indexes
    __table_args__ = (
        Index("ix_articles_ranking", "flag", "ai_status", "is_duplicate", "rank_score"),
        Index("ix_articles_created_flag", "created_at", "flag"),
        Index("ix_articles_category_flag", "category", "flag"),
    )
```

### In-Memory Structures

```python
# AI Service Result Structure
AIResult = Dict[str, Any]
{
    "rephrased_title": str,
    "rephrased_content": str,      # HTML formatted
    "telugu_title": str,
    "telugu_content": str,         # HTML formatted
    "category": str,
    "tags": List[str],
    "slug": str,
    "method": str,                  # Processing method used
    "ai_status_code": str,         # Success/failure indicator
    "similarity_score": float,     # 0.0-1.0 similarity to source
    "image_url": str
}

# Provider Response Structure
ProviderResponse = Dict[str, Any]
{
    "success": bool,
    "content": str,                # Raw AI response
    "model": str,                  # Model used
    "tokens": int,                 # Token count
    "latency_ms": int,             # Processing time
    "error": Optional[str]          # Error message if failed
}
```

---

## Core Algorithms

### 1. Similarity Validation Algorithm

```python
def compute_similarity(a: str, b: str) -> float:
    """
    Gestalt pattern matching similarity.
    
    Algorithm:
    1. Strip HTML tags from both strings
    2. Normalize whitespace and case
    3. Apply SequenceMatcher ratio
    4. Return 0.0-1.0 similarity score
    
    Threshold: 0.70 (70% maximum allowed similarity)
    """
    
def validate_similarity(original: str, rephrased: str) -> bool:
    """
    Similarity validation with retry logic.
    
    Flow:
    1. Compute similarity scores for title and content
    2. Check both <= 0.70 threshold
    3. If failed, trigger retry with stronger prompt
    4. If retry fails, fallback to local engine
    """
```

### 2. Source Name Stripping Algorithm

```python
def _strip_source_names(text: str) -> str:
    """
    Copyright compliance through source attribution removal.
    
    Algorithm:
    1. Telugu source prefix patterns (regex)
    2. Standalone source name occurrences
    3. Source attribution phrases
    4. General replacement with "Peoples Feedback"
    
    Patterns Handled:
    - "SourceName, City: ..."
    - "(SourceName)"
    - "- SourceName"
    - "according to SourceName"
    - "SourceName report"
    """
```

### 3. Category Auto-Detection Algorithm

```python
def _auto_category(title: str, content: str) -> str:
    """
    Keyword-based category classification.
    
    Algorithm:
    1. Concatenate title + first 1500 chars of content
    2. Lowercase and normalize
    3. Check against category keyword dictionaries
    4. Return first match or "Home" as default
    
    Category Keywords Example:
    "Andhra Pradesh": ["andhra", "ap ", "vijayawada", "jagan"]
    "Sports": ["cricket", "football", "match", "ipl", "player"]
    "Tech": ["ai ", "technology", "google", "apple", "software"]
    """
```

### 4. Batch Processing Algorithm

```python
def process_ai_batch():
    """
    High-performance batch processing algorithm.
    
    Steps:
    1. Stuck Article Recovery
       - Find articles in "processing" > 5 minutes
       - Reset to "pending" status
       - Log recovery count
    
    2. Batch Selection
       - Query pending articles (ai_status IN ["pending", "unknown"])
       - Exclude duplicates (is_duplicate = False)
       - Random order for fairness
       - Limit by AI_BATCH_SIZE config
    
    3. Atomic Status Update
       - Mark selected articles as "processing"
       - Prevent concurrent processing
    
    4. Parallel Processing
       - ThreadPoolExecutor with max_workers = min(AI_CONCURRENCY, 8)
       - 120-second timeout per article
       - 300-second timeout per batch
    
    5. Result Aggregation
       - Count successes/failures
       - Log performance metrics
       - Trigger downstream tasks (ranking, sync)
    """
```

---

## API Contracts

### 1. AI Service Interface

```python
# Primary Processing Interface
def process_article(
    title: str,
    content: str,
    source_name: str = "Unknown"
) -> Dict[str, Any]:
    """
    Process article through AI rephrasing pipeline.
    
    Parameters:
    - title: Original article title (required)
    - content: Original article content (required)
    - source_name: Source identifier for routing logic
    
    Returns:
    {
        "rephrased_title": str,
        "rephrased_content": str,      # HTML formatted
        "telugu_title": str,
        "telugu_content": str,         # HTML formatted
        "category": str,
        "tags": List[str],
        "slug": str,
        "method": str,                  # gemini/openai/local_paraphrase/etc
        "ai_status_code": str,          # AI_SUCCESS/LOCAL_PARAPHRASE/etc
        "similarity_score": float,
        "image_url": str
    }
    
    Status Codes:
    - AI_SUCCESS: Cloud AI passed similarity check
    - AI_RETRY_SUCCESS: Cloud AI passed on retry
    - LOCAL_PARAPHRASE: Local engine used (Google News or cloud failure)
    - REWRITE_FAILED: All attempts failed, sent to admin queue
    - GOOGLE_NEWS_LOCAL: Google News processed locally
    """
```

### 2. Paraphrase Engine Interface

```python
def paraphrase_to_html(
    title: str,
    content: str,
    seed: int = 42
) -> Dict[str, str]:
    """
    Local paraphrase processing.
    
    Parameters:
    - title: Input title
    - content: Input content (HTML or plain text)
    - seed: Random seed for reproducible results
    
    Returns:
    {
        "rephrased_title": str,
        "rephrased_content": str      # Structured HTML
    }
    """
    
def fast_paraphrase(
    text: str,
    seed: int = 42
) -> str:
    """
    Plain text paraphrase (no HTML formatting).
    
    Parameters:
    - text: Input text to paraphrase
    - seed: Random seed for consistency
    
    Returns:
    - str: Paraphrased plain text
    """
```

### 3. Task Queue Interface

```python
# Celery Task Definitions
@celery_app.task(name="app.tasks.celery_app.process_ai_batch")
def process_ai_batch() -> None:
    """
    Process pending articles through AI pipeline.
    
    Triggered by:
    - Scheduled cron (every AI processing interval)
    - Manual trigger via scheduler API
    - Auto-trigger after scraping completion
    
    Side Effects:
    - Updates article records in database
    - Triggers ranking and sync tasks
    - Logs processing metrics
    """
    
@celery_app.task(name="app.tasks.celery_app.worker_process_ai")
def worker_process_ai(article_id: int) -> bool:
    """
    Process individual article.
    
    Parameters:
    - article_id: Database record identifier
    
    Returns:
    - bool: Success (True) or failure (False)
    
    Side Effects:
    - Updates article fields
    - Increments ai_error_count on failure
    - Sets ai_status accordingly
    """
```

---

## Error Handling

### 1. Provider Failure Handling

```python
def _try_cloud_providers(self, prompt: str, best_only: bool = False) -> Optional[str]:
    """
    Sequential provider fallback with comprehensive error handling.
    
    Error Categories:
    1. Network Errors (timeout, connection refused)
    2. API Errors (rate limiting, invalid key)
    3. Model Errors (content policy, token limits)
    4. Parse Errors (invalid JSON response)
    
    Handling Strategy:
    - Log error with provider and model details
    - Continue to next provider in chain
    - Track failure counts for circuit breaker logic
    - Return None if all providers exhausted
    """
    
# Error Recovery Flow
try:
    response = provider.generate_content(prompt, config)
    if response and response.text:
        return response.text
except Exception as exc:
    logger.warning(f"[AI] {provider}/{model} failed: {exc}")
    # Continue to next provider
```

### 2. Similarity Validation Failure

```python
def handle_similarity_failure(original_title: str, original_content: str) -> Dict:
    """
    Handle similarity threshold violations.
    
    Scenarios:
    1. First attempt failed (similarity > 0.70)
       - Retry with stronger prompt
       - Emphasize sentence restructuring
       - Require 100% rewrite
    
    2. Retry attempt failed
       - Fallback to local ParaphraseEngine
       - Mark as LOCAL_PARAPHRASE (public)
       - Log similarity scores for analysis
    
    3. Local engine also fails
       - Mark as REWRITE_FAILED
       - Send to admin approval queue
       - Use minimal HTML fallback
    """
```

### 3. Database Transaction Handling

```python
def atomic_article_update(article_id: int, result: Dict) -> bool:
    """
    Atomic database update with rollback on failure.
    
    Transaction Pattern:
    1. Begin transaction
    2. Lock article record (SELECT FOR UPDATE)
    3. Update all fields in single operation
    4. Commit if successful, rollback on error
    5. Return success status
    """
    
    try:
        with db.begin():
            article = db.execute(
                select(NewsArticle).where(NewsArticle.id == article_id).with_for_update()
            ).scalar_one()
            
            # Update all fields
            article.rephrased_title = result["rephrased_title"]
            article.rephrased_content = result["rephrased_content"]
            article.telugu_title = result["telugu_title"]
            article.telugu_content = result["telugu_content"]
            article.category = result["category"]
            article.tags = result["tags"]
            article.slug = result["slug"]
            article.ai_status = "success"
            article.processed_at = datetime.now(timezone.utc)
            
            # Auto-commit on success
        return True
        
    except Exception as exc:
        logger.error(f"[DB] Update failed for article {article_id}: {exc}")
        return False
```

### 4. Stuck Article Recovery

```python
def recover_stuck_articles():
    """
    Automatic recovery of articles stuck in processing state.
    
    Detection Logic:
    - Articles with ai_status = "processing"
    - Updated timestamp > 5 minutes ago
    - No active job execution record
    
    Recovery Actions:
    1. Reset ai_status to "pending"
    2. Increment ai_error_count
    3. Log recovery details
    4. Allow reprocessing in next batch
    """
    
    stuck_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    stuck_reset = db.execute(
        update(NewsArticle)
        .where(
            NewsArticle.ai_status == "processing",
            NewsArticle.updated_at < stuck_cutoff
        )
        .values(
            ai_status="pending",
            updated_at=func.now(),
            ai_error_count = NewsArticle.ai_error_count + 1
        )
    )
```

---

## Performance Considerations

### 1. Memory Management

```python
# Singleton Pattern for ParaphraseEngine
class ParaphraseEngine:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance
    
    # Benefits:
    # - Single synonym dictionary in memory
    # - Zero repeated model loading
    # - Thread-safe access
```

### 2. Concurrency Control

```python
# ThreadPoolExecutor Configuration
MAX_WORKERS = min(settings.AI_CONCURRENCY, 8)
TIMEOUT_PER_ARTICLE = 120  # seconds
TIMEOUT_PER_BATCH = 300    # seconds

# Worker Pool Benefits:
# - Parallel processing of articles
# - Controlled resource usage
# - Timeout protection against hangs
# - Automatic cleanup on completion
```

### 3. Database Optimization

```python
# Strategic Indexing
class NewsArticle(Base):
    __table_args__ = (
        # Primary query pattern for batch processing
        Index("ix_articles_ranking", "flag", "ai_status", "is_duplicate", "rank_score"),
        
        # Time-based queries for cleanup
        Index("ix_articles_created_flag", "created_at", "flag"),
        
        # Category-based filtering
        Index("ix_articles_category_flag", "category", "flag"),
        
        # Duplicate detection
        Index("ix_articles_content_hash", "content_hash"),
    )

# Query Optimization
def fetch_pending_articles():
    """
    Optimized query for batch processing.
    
    Optimizations:
    1. Specific column selection (id only)
    2. Indexed WHERE conditions
    3. RANDOM() for fair distribution
    4. LIMIT for batch size control
    """
    return db.execute(
        select(NewsArticle.id)
        .where(
            NewsArticle.ai_status.in_(["pending", "unknown"]),
            NewsArticle.is_duplicate == False,
        )
        .order_by(func.random())
        .limit(settings.AI_BATCH_SIZE)
    ).fetchall()
```

### 4. Caching Strategy

```python
# In-Memory Caching for Categories
class CategoryService:
    _categories = {}
    _last_refresh = None
    
    def normalize(self, category: str) -> str:
        """
        Cached category normalization.
        
        Cache Strategy:
        - Load categories once per hour
        - In-memory lookup for performance
        - Background refresh on expiry
        """
        
        if not self._categories or self._is_cache_expired():
            self._refresh_cache()
        
        return self._categories.get(category.lower(), "Home")
```

---

## Security Implementation

### 1. API Key Management

```python
# Multi-Key Redundancy
class AIService:
    GEMINI_KEYS = [
        settings.GEMINI_API_KEY,
        settings.GEMINI_API_KEY_SECONDARY,
        settings.GEMINI_API_KEY_TERTIARY,
    ]
    
    def _try_gemini(self, api_key: str, prompt: str, label: str) -> Optional[str]:
        """
        Secure API key usage with rotation.
        
        Security Measures:
        1. Keys stored in environment variables
        2. Automatic key rotation on failure
        3. No key logging in production
        4. Rate limiting per key
        """
```

### 2. Input Sanitization

```python
def _clean(text: str) -> str:
    """
    Input sanitization for security and compliance.
    
    Sanitization Steps:
    1. Remove prompt injection attempts
    2. Strip malicious HTML tags
    3. Remove source attributions
    4. Normalize whitespace
    
    Threats Mitigated:
    - Prompt injection attacks
    - XSS through malicious HTML
    - Copyright violations
    """
    
    for pattern in [
        r"(?i)ignore\s+previous\s+instructions.*",
        r"(?i)system\s+prompt.*",
        r"(?i)act\s+as\s+.*",
    ]:
        text = re.sub(pattern, "", text)
    
    return _strip_source_names(text).strip()
```

### 3. Content Validation

```python
def _validate_dict(d: Dict, orig_title: str, orig_content: str) -> Dict:
    """
    Output validation and sanitization.
    
    Validation Checks:
    1. Required field presence
    2. Data type verification
    3. Content length limits
    4. HTML tag sanitization
    5. Source name removal
    """
    
    # Field validation
    title = _strip_source_names(str(d.get("title", "")).strip()) or orig_title
    content = _strip_source_names(str(d.get("content", "")).strip()) or orig_content
    
    # Category normalization
    try:
        cat = category_service.normalize(str(d.get("category", "Home")))
    except Exception:
        cat = "Home"
    
    # Tag validation
    tags = d.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip().lower() for t in tags if str(t).strip()][:5]
    
    return {
        "rephrased_title": title,
        "rephrased_content": content,
        "category": cat,
        "tags": tags,
        # ... other fields
    }
```

### 4. Access Control

```python
# Admin-Only Operations
@router.post("/api/articles/{article_id}/reprocess")
async def reprocess_article(
    article_id: int,
    current_user: AdminUser = Depends(require_admin)
):
    """
    Restricted article reprocessing.
    
    Access Control:
    1. Admin authentication required
    2. Role-based permissions
    3. Audit logging
    4. Rate limiting per user
    """
    
    # Log admin action
    logger.info(f"[ADMIN] {current_user.username} reprocessing article {article_id}")
    
    # Process with elevated privileges
    result = await asyncio.to_thread(
        ai_service.process_article,
        article.original_title,
        article.original_content,
        source_name=article.source.name
    )
```

---

## Monitoring and Observability

### 1. Performance Metrics

```python
# Processing Time Tracking
def process_article_with_metrics(title: str, content: str) -> Dict:
    """
    Comprehensive performance monitoring.
    
    Metrics Collected:
    1. Total processing time
    2. Provider-specific latency
    3. Similarity computation time
    4. Database update time
    5. Memory usage
    """
    
    start_time = time.time()
    
    # Track provider performance
    provider_metrics = {}
    for provider in PROVIDERS:
        provider_start = time.time()
        result = _try_provider(provider, prompt)
        provider_metrics[provider] = {
            "latency_ms": (time.time() - provider_start) * 1000,
            "success": result is not None,
            "tokens_used": estimate_tokens(prompt, result) if result else 0
        }
        
        if result:
            break
    
    # Log metrics
    logger.info(f"[METRICS] Article processed in {(time.time() - start_time)*1000:.2f}ms")
    logger.debug(f"[METRICS] Provider performance: {provider_metrics}")
```

### 2. Error Tracking

```python
# Structured Error Logging
def log_processing_error(article_id: int, error: Exception, context: Dict):
    """
    Comprehensive error tracking.
    
    Error Context:
    1. Article metadata
    2. Provider attempted
    3. Error type and message
    4. Processing stage
    5. Retry count
    """
    
    error_data = {
        "article_id": article_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "provider": context.get("provider"),
        "stage": context.get("stage"),
        "retry_count": context.get("retry_count", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    logger.error(f"[ERROR] Processing failed: {error_data}", exc_info=True)
    
    # Update error tracking in database
    db.execute(
        update(NewsArticle)
        .where(NewsArticle.id == article_id)
        .values(
            ai_error_count = NewsArticle.ai_error_count + 1,
            ai_status = "failed"
        )
    )
```

---

## Configuration Management

### 1. Environment Variables

```python
# AI Processing Configuration
AI_CONCURRENCY = os.getenv("AI_CONCURRENCY", "4")
AI_BATCH_SIZE = os.getenv("AI_BATCH_SIZE", "50")
AI_TIMEOUT_SECONDS = os.getenv("AI_TIMEOUT_SECONDS", "120")

# Provider Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY_SECONDARY = os.getenv("GEMINI_API_KEY_SECONDARY")
GEMINI_API_KEY_TERTIARY = os.getenv("GEMINI_API_KEY_TERTIARY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")

# Similarity Thresholds
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.70"))
SIMILARITY_RETRY_THRESHOLD = float(os.getenv("SIMILARITY_RETRY_THRESHOLD", "0.70"))

# Processing Flags
SCHEDULE_AI_ENABLED = os.getenv("SCHEDULE_AI_ENABLED", "true").lower() == "true"
IS_LOCAL_DEV = os.getenv("IS_LOCAL_DEV", "false").lower() == "true"
```

### 2. Dynamic Configuration

```python
# Runtime Configuration Updates
class ConfigManager:
    """
    Dynamic configuration management.
    
    Features:
    1. Hot-reload configuration changes
    2. Environment-specific overrides
    3. Feature flags
    4. Rate limiting controls
    """
    
    @classmethod
    def get_ai_config(cls) -> Dict[str, Any]:
        """
        Get current AI processing configuration.
        
        Returns:
        {
            "batch_size": int,
            "concurrency": int,
            "timeout": int,
            "similarity_threshold": float,
            "providers_enabled": List[str],
            "feature_flags": Dict[str, bool]
        }
        """
        
        return {
            "batch_size": settings.AI_BATCH_SIZE,
            "concurrency": settings.AI_CONCURRENCY,
            "timeout": settings.AI_TIMEOUT_SECONDS,
            "similarity_threshold": settings.SIMILARITY_THRESHOLD,
            "providers_enabled": cls._get_enabled_providers(),
            "feature_flags": {
                "telugu_translation": settings.TELUGU_TRANSLATION_ENABLED,
                "similarity_check": settings.SIMILARITY_CHECK_ENABLED,
                "auto_ranking": settings.AUTO_RANKING_ENABLED,
            }
        }
```

---

## Deployment Considerations

### 1. Scaling Strategy

```python
# Horizontal Scaling
class ScalingManager:
    """
    Auto-scaling configuration for AI processing.
    
    Scaling Factors:
    1. Queue depth (pending articles)
    2. Processing latency
    3. Error rates
    4. Resource utilization
    """
    
    def calculate_optimal_workers(self) -> int:
        """
        Dynamic worker calculation.
        
        Formula:
        workers = min(
            max(1, queue_depth // 10),
            CPU cores * 2,
            50  # Maximum hard limit
        )
        """
        
        queue_depth = self.get_pending_count()
        cpu_cores = os.cpu_count()
        
        return min(
            max(1, queue_depth // 10),
            cpu_cores * 2,
            50
        )
```

### 2. Resource Management

```python
# Memory and CPU Optimization
class ResourceMonitor:
    """
    Resource usage monitoring and optimization.
    
    Metrics Tracked:
    1. Memory usage per worker
    2. CPU utilization
    3. Database connection pool
    4. API rate limits
    """
    
    def monitor_resources(self):
        """
        Continuous resource monitoring.
        
        Actions:
        1. Log resource usage
        2. Trigger scaling events
        3. Clean up idle connections
        4. Adjust batch sizes
        """
        
        import psutil
        
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=1)
        
        if memory_usage > 80:
            logger.warning(f"[RESOURCE] High memory usage: {memory_usage}%")
            self.reduce_batch_size()
        
        if cpu_usage > 90:
            logger.warning(f"[RESOURCE] High CPU usage: {cpu_usage}%")
            self.reduce_concurrency()
```

This comprehensive low-level design document provides detailed implementation guidance for the AI Rephrasing System, covering all critical aspects from algorithms to deployment considerations.
