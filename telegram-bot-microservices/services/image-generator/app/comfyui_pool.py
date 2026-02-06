"""
ComfyUI Pool Manager
Manages multiple ComfyUI instances for parallel processing
"""
import os
import threading
from typing import Optional, List

from app.config import config
from shared.utils import get_logger

logger = get_logger(__name__)


class ComfyUIPoolManager:
    """
    Manages pool of ComfyUI servers for parallel generation.
    Each Celery worker gets assigned to a specific ComfyUI instance.
    """

    def __init__(self):
        self.comfyui_urls: List[str] = config.COMFYUI_URLS
        self.worker_assignments = {}  # {worker_id: comfyui_url}
        self.lock = threading.Lock()

        logger.info(f"Initialized ComfyUI pool with {len(self.comfyui_urls)} instances: {self.comfyui_urls}")

    def get_worker_id(self) -> int:
        """
        Get current Celery worker ID based on hostname.
        Format: image-generator@hostname -> extract index

        Returns:
            Worker ID (0-based index)
        """
        hostname = os.environ.get("HOSTNAME", "")
        # For local testing without Celery
        if not hostname:
            import threading
            return threading.current_thread().ident % len(self.comfyui_urls)

        # Extract worker index from Celery pool
        # Celery uses ForkPoolWorker-1, ForkPoolWorker-2, etc in process name
        try:
            import multiprocessing
            process_name = multiprocessing.current_process().name
            if "ForkPoolWorker" in process_name or "Worker" in process_name:
                # Extract number from "ForkPoolWorker-1" -> 1
                parts = process_name.split("-")
                if len(parts) > 1 and parts[-1].isdigit():
                    worker_num = int(parts[-1])
                    # Convert to 0-based index
                    return (worker_num - 1) % len(self.comfyui_urls)
        except Exception as e:
            logger.warning(f"Could not extract worker ID from process name: {e}")

        # Fallback: use thread ID modulo
        return threading.current_thread().ident % len(self.comfyui_urls)

    def get_comfyui_url(self) -> str:
        """
        Get ComfyUI URL for current worker.
        Each worker is assigned to a specific ComfyUI instance for worker affinity.

        Returns:
            ComfyUI base URL
        """
        worker_id = self.get_worker_id()

        with self.lock:
            # Check if already assigned
            if worker_id in self.worker_assignments:
                url = self.worker_assignments[worker_id]
                logger.debug(f"Worker {worker_id} using assigned ComfyUI: {url}")
                return url

            # Assign worker to ComfyUI instance (round-robin)
            comfyui_index = worker_id % len(self.comfyui_urls)
            assigned_url = self.comfyui_urls[comfyui_index]
            self.worker_assignments[worker_id] = assigned_url

            logger.info(f"Assigned Worker {worker_id} -> ComfyUI {assigned_url}")
            return assigned_url

    def get_all_urls(self) -> List[str]:
        """
        Get all ComfyUI URLs in the pool.

        Returns:
            List of ComfyUI base URLs
        """
        return self.comfyui_urls.copy()


# Global pool manager instance
comfyui_pool = ComfyUIPoolManager()
