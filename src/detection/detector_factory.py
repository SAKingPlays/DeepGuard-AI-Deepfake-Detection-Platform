"""Unified detector factory with automatic provider fallback."""
from __future__ import annotations
import os
import time
import hashlib
import logging
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from src.detection.base_detector import BaseDetector, DetectionResult
from src.detection.gemini_detector import GeminiDetector
from src.detection.openai_detector import OpenAIDetector
from src.detection.local_detector import LocalDetector
from src.config import GEMINI_API_KEY

logger = logging.getLogger("deepguard")


@dataclass
class ProviderStatus:
    """Track provider health and rate limiting."""
    name: str
    available: bool = True
    last_error: Optional[str] = None
    last_used: float = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0


class SmartDetectorFactory:
    """
    Intelligent detector factory with:
    - Automatic provider fallback
    - Rate limiting and cooldown
    - Response caching
    - Provider health tracking
    """
    
    # Cooldown periods after failures (seconds)
    COOLDOWN_SHORT = 30    # 30 seconds
    COOLDOWN_MEDIUM = 300  # 5 minutes
    COOLDOWN_LONG = 3600   # 1 hour
    
    # Max consecutive failures before longer cooldown
    MAX_FAILURES_SHORT = 2
    MAX_FAILURES_MEDIUM = 5
    
    def __init__(self, enable_cache: bool = True):
        self.enable_cache = enable_cache
        self._cache: Dict[str, DetectionResult] = {}
        self._cache_ttl = 3600  # 1 hour cache
        
        # Initialize providers
        self._providers: List[BaseDetector] = []
        self._provider_status: Dict[str, ProviderStatus] = {}
        
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers."""
        # Priority order: Gemini -> OpenAI -> Local
        
        # 1. Gemini (if API key available)
        if GEMINI_API_KEY and GEMINI_API_KEY != "":
            try:
                gemini = GeminiDetector(api_key=GEMINI_API_KEY)
                self._providers.append(gemini)
                self._provider_status["gemini"] = ProviderStatus("Gemini 2.0")
                logger.info("✓ Gemini provider registered")
            except Exception as e:
                logger.warning(f"✗ Gemini initialization failed: {e}")
        
        # 2. OpenAI (if API key available)
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            try:
                openai = OpenAIDetector(api_key=openai_key)
                self._providers.append(openai)
                self._provider_status["openai"] = ProviderStatus("OpenAI GPT-4o")
                logger.info("✓ OpenAI provider registered")
            except Exception as e:
                logger.warning(f"✗ OpenAI initialization failed: {e}")
        
        # 3. Local detector (always available, no API needed)
        try:
            local = LocalDetector()
            self._providers.append(local)
            self._provider_status["local"] = ProviderStatus("Local CV")
            logger.info("✓ Local CV provider registered (offline fallback)")
        except Exception as e:
            logger.error(f"✗ Local detector failed: {e}")
        
        if not self._providers:
            raise RuntimeError("No detection providers available!")
        
        logger.info(f"Factory initialized with {len(self._providers)} provider(s)")
    
    def _get_cache_key(self, filepath: str, **kwargs) -> str:
        """Generate cache key for file."""
        # Hash file content + modification time + kwargs
        try:
            stat = os.stat(filepath)
            mtime = str(stat.st_mtime)
            size = str(stat.st_size)
        except:
            mtime = "0"
            size = "0"
        
        key_str = f"{filepath}:{mtime}:{size}:{str(kwargs)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[DetectionResult]:
        """Get cached result if still valid."""
        if not self.enable_cache:
            return None
        
        if cache_key in self._cache:
            result = self._cache[cache_key]
            age = time.time() - result.processing_time
            if age < self._cache_ttl:
                logger.info(f"Cache hit (age: {age:.0f}s)")
                return result
            else:
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: DetectionResult):
        """Cache detection result."""
        if self.enable_cache:
            self._cache[cache_key] = result
    
    def _is_provider_available(self, provider_name: str) -> bool:
        """Check if provider is available (not in cooldown)."""
        if provider_name not in self._provider_status:
            return False
        
        status = self._provider_status[provider_name]
        if not status.available:
            return False
        
        if time.time() < status.cooldown_until:
            remaining = int(status.cooldown_until - time.time())
            logger.debug(f"{provider_name} in cooldown ({remaining}s remaining)")
            return False
        
        return True
    
    def _mark_provider_failed(self, provider_name: str, error: str):
        """Mark provider as failed and set cooldown."""
        if provider_name not in self._provider_status:
            return
        
        status = self._provider_status[provider_name]
        status.consecutive_failures += 1
        status.last_error = error
        
        # Determine cooldown duration
        if status.consecutive_failures >= self.MAX_FAILURES_MEDIUM:
            cooldown = self.COOLDOWN_LONG
        elif status.consecutive_failures >= self.MAX_FAILURES_SHORT:
            cooldown = self.COOLDOWN_MEDIUM
        else:
            cooldown = self.COOLDOWN_SHORT
        
        status.cooldown_until = time.time() + cooldown
        logger.warning(f"{provider_name} failed ({status.consecutive_failures}x), "
                      f"cooldown for {cooldown}s: {error[:100]}")
    
    def _mark_provider_success(self, provider_name: str):
        """Reset failure count on success."""
        if provider_name in self._provider_status:
            status = self._provider_status[provider_name]
            if status.consecutive_failures > 0:
                logger.info(f"{provider_name} recovered")
            status.consecutive_failures = 0
            status.last_error = None
            status.last_used = time.time()
    
    def get_provider_names(self) -> List[str]:
        """Get list of registered provider names."""
        return list(self._provider_status.keys())
    
    def ensure_loaded(self):
        """Ensure all providers are loaded (compatibility with DetectionWorker)."""
        for provider in self._providers:
            provider.ensure_loaded()
    
    def get_provider_status(self) -> Dict[str, ProviderStatus]:
        """Get current status of all providers."""
        return self._provider_status.copy()
    
    def detect(self, filepath: str, progress_cb: Optional[Callable] = None,
               cancel_flag: Optional[list] = None, **kwargs) -> DetectionResult:
        """
        Detect with automatic provider fallback.
        
        Tries providers in priority order until one succeeds.
        Uses caching and respects rate limits.
        """
        cache_key = self._get_cache_key(filepath, **kwargs)
        
        # Check cache first
        cached = self._get_cached_result(cache_key)
        if cached:
            if progress_cb:
                progress_cb(100, "Using cached result")
            return cached
        
        last_error = None
        
        for provider in self._providers:
            provider_name = provider.__class__.__name__.replace("Detector", "").lower()
            
            # Skip if in cooldown
            if not self._is_provider_available(provider_name):
                continue
            
            try:
                if progress_cb:
                    progress_cb(0, f"Trying {self._provider_status[provider_name].name}...")
                
                logger.info(f"Attempting detection with {provider_name}")
                result = provider.detect(filepath, progress_cb, cancel_flag, **kwargs)
                
                # Check if result is valid (not an error)
                if result.error is None:
                    self._mark_provider_success(provider_name)
                    self._cache_result(cache_key, result)
                    logger.info(f"✓ {provider_name} succeeded: {result.verdict}")
                    return result
                else:
                    # Provider returned error but didn't raise
                    last_error = result.error
                    self._mark_provider_failed(provider_name, result.error)
                    if progress_cb:
                        progress_cb(0, f"{provider_name} failed, trying next...")
            
            except Exception as e:
                last_error = str(e)
                self._mark_provider_failed(provider_name, last_error)
                if progress_cb:
                    progress_cb(0, f"{provider_name} error, trying next...")
                continue
        
        # All providers failed
        logger.error("All detection providers failed")
        return DetectionResult(
            media_type="image",
            filepath=filepath,
            is_fake=False,
            confidence=0.0,
            verdict="ERROR",
            verdict_color="#FF5252",
            error=f"All providers failed. Last error: {last_error}",
            processing_time=0,
            model_used="All Providers (failed)"
        )
    
    def clear_cache(self):
        """Clear detection cache."""
        self._cache.clear()
        logger.info("Detection cache cleared")


# Singleton factory instance
_factory: Optional[SmartDetectorFactory] = None

def get_detector_factory() -> SmartDetectorFactory:
    """Get or create the singleton detector factory."""
    global _factory
    if _factory is None:
        _factory = SmartDetectorFactory()
    return _factory

def reset_detector_factory():
    """Reset the factory (useful for testing or config changes)."""
    global _factory
    _factory = None
    logger.info("Detector factory reset")
