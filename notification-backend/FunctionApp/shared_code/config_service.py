import logging
import time
import os
from typing import Dict, List, Optional, Any, Union
from cachetools import TTLCache
from .config_repository_cosmosdb import ConfigRepository

class CachedConfigService:
    """Service with caching for configuration access"""
    
    def __init__(self, config_repository: ConfigRepository):
        """Initialize with repository and cache settings"""
        self.repo = config_repository
        
        # Get cache expiration from environment, default to 10 minutes
        cache_ttl = int(os.environ.get("CACHE_EXPIRATION_MINUTES", 10)) * 60
        
        # Create TTL cache with max size 1000 items
        self.cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        logging.info(f"CachedConfigService initialized with {cache_ttl}s TTL")
    
    async def get_config(self, partition_key: str, row_key: str) -> Optional[Dict[str, Any]]:
        """Get configuration with caching"""
        cache_key = f"{partition_key}:{row_key}"
        
        # Try to get from cache first
        if cache_key in self.cache:
            logging.info(f"Cache hit: {cache_key}")
            return self.cache[cache_key]
        
        # Not in cache, get from repository
        logging.info(f"Cache miss: {cache_key}")
        result = await self.repo.get_config(partition_key, row_key)
        
        # Cache the result (even if None, to prevent repeated lookups for missing values)
        if result is not None:
            self.cache[cache_key] = result
        
        return result
    
    async def get_config_by_partition(self, partition_key: str) -> List[Dict[str, Any]]:
        """Get all configs for a partition with caching"""
        cache_key = f"partition:{partition_key}"
        
        # Try to get from cache first
        if cache_key in self.cache:
            logging.info(f"Cache hit: {cache_key}")
            return self.cache[cache_key]
        
        # Not in cache, get from repository
        logging.info(f"Cache miss: {cache_key}")
        result = await self.repo.get_config_by_partition(partition_key)
        
        # Cache the result
        self.cache[cache_key] = result
        
        return result
    
    async def get_config_by_pattern(self, partition_key: str, row_key_pattern: str) -> List[Dict[str, Any]]:
        """Get configs matching a pattern with caching"""
        cache_key = f"pattern:{partition_key}:{row_key_pattern}"
        
        # Try to get from cache first
        if cache_key in self.cache:
            logging.info(f"Cache hit: {cache_key}")
            return self.cache[cache_key]
        
        # Not in cache, get from repository
        logging.info(f"Cache miss: {cache_key}")
        result = await self.repo.get_config_by_pattern(partition_key, row_key_pattern)
        
        # Cache the result
        self.cache[cache_key] = result
        
        return result
    
    def invalidate_cache(self, partition_key: Optional[str] = None, row_key: Optional[str] = None):
        """Invalidate specific cache entries or all if no keys provided"""
        if partition_key and row_key:
            # Remove specific entry
            cache_key = f"{partition_key}:{row_key}"
            if cache_key in self.cache:
                del self.cache[cache_key]
                logging.info(f"Invalidated cache for {cache_key}")
        
        elif partition_key:
            # Remove partition entries
            cache_key = f"partition:{partition_key}"
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            # Also remove any pattern entries for this partition
            pattern_keys = [k for k in self.cache if k.startswith(f"pattern:{partition_key}:")]
            for k in pattern_keys:
                del self.cache[k]
            
            logging.info(f"Invalidated cache for partition {partition_key}")
        
        else:
            # Clear entire cache
            self.cache.clear()
            logging.info("Cleared entire configuration cache")