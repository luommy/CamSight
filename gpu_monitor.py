"""
GPU Monitoring Module
Supports multiple platforms: NVIDIA (NVML), Jetson Orin (tegrastats), Apple Silicon, AMD
"""
import asyncio
import logging
import psutil
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from collections import deque

logger = logging.getLogger(__name__)


class GPUMonitor(ABC):
    """Abstract base class for GPU monitoring"""

    def __init__(self, history_size: int = 60):
        """
        Initialize GPU monitor

        Args:
            history_size: Number of historical data points to keep (default 60 = 1 minute at 1Hz)
        """
        self.history_size = history_size
        self.gpu_util_history = deque(maxlen=history_size)
        self.vram_used_history = deque(maxlen=history_size)
        self.cpu_util_history = deque(maxlen=history_size)
        self.ram_used_history = deque(maxlen=history_size)

    @abstractmethod
    def get_stats(self) -> Dict:
        """Get current GPU and system stats"""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup resources"""
        pass

    def get_cpu_ram_stats(self) -> Dict:
        """Get CPU and RAM stats (common across all platforms)"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            return {
                "cpu_percent": cpu_percent,
                "ram_used_gb": memory.used / (1024**3),
                "ram_total_gb": memory.total / (1024**3),
                "ram_percent": memory.percent
            }
        except Exception as e:
            logger.error(f"Error getting CPU/RAM stats: {e}")
            return {
                "cpu_percent": 0,
                "ram_used_gb": 0,
                "ram_total_gb": 0,
                "ram_percent": 0
            }

    def update_history(self, stats: Dict):
        """Update historical data"""
        self.gpu_util_history.append(stats.get("gpu_percent", 0))
        self.vram_used_history.append(stats.get("vram_used_gb", 0))
        self.cpu_util_history.append(stats.get("cpu_percent", 0))
        self.ram_used_history.append(stats.get("ram_used_gb", 0))

    def get_history(self) -> Dict[str, List[float]]:
        """Get historical data as lists"""
        return {
            "gpu_util": list(self.gpu_util_history),
            "vram_used": list(self.vram_used_history),
            "cpu_util": list(self.cpu_util_history),
            "ram_used": list(self.ram_used_history)
        }


class NVMLMonitor(GPUMonitor):
    """NVIDIA GPU monitoring using NVML (for Desktop, DGX, Jetson Thor)"""

    def __init__(self, device_index: int = 0, history_size: int = 60):
        """
        Initialize NVML monitor

        Args:
            device_index: GPU device index (default 0)
            history_size: Number of historical data points to keep
        """
        super().__init__(history_size)
        self.device_index = device_index
        self.handle = None
        self.available = False

        try:
            import pynvml
            pynvml.nvmlInit()
            self.handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
            self.device_name = pynvml.nvmlDeviceGetName(self.handle)
            if isinstance(self.device_name, bytes):
                self.device_name = self.device_name.decode('utf-8')
            self.available = True
            logger.info(f"NVML initialized for GPU: {self.device_name}")
        except Exception as e:
            logger.warning(f"NVML not available: {e}")
            self.available = False

    def get_stats(self) -> Dict:
        """Get current GPU stats using NVML"""
        if not self.available:
            return self._get_fallback_stats()

        try:
            import pynvml

            # Get GPU utilization
            utilization = pynvml.nvmlDeviceGetUtilizationRates(self.handle)
            gpu_percent = utilization.gpu

            # Get memory info
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            vram_used_gb = memory_info.used / (1024**3)
            vram_total_gb = memory_info.total / (1024**3)
            vram_percent = (memory_info.used / memory_info.total) * 100

            # Get temperature
            try:
                temp = pynvml.nvmlDeviceGetTemperature(self.handle, pynvml.NVML_TEMPERATURE_GPU)
            except:
                temp = None

            # Get power usage
            try:
                power_mw = pynvml.nvmlDeviceGetPowerUsage(self.handle)
                power_w = power_mw / 1000.0
            except:
                power_w = None

            # Get CPU and RAM stats
            system_stats = self.get_cpu_ram_stats()

            stats = {
                "platform": "NVIDIA (NVML)",
                "gpu_name": self.device_name,
                "gpu_percent": gpu_percent,
                "vram_used_gb": vram_used_gb,
                "vram_total_gb": vram_total_gb,
                "vram_percent": vram_percent,
                "temp_c": temp,
                "power_w": power_w,
                **system_stats
            }

            # Update history
            self.update_history(stats)

            return stats

        except Exception as e:
            logger.error(f"Error getting NVML stats: {e}")
            return self._get_fallback_stats()

    def _get_fallback_stats(self) -> Dict:
        """Fallback stats when GPU not available"""
        system_stats = self.get_cpu_ram_stats()
        return {
            "platform": "NVIDIA (NVML unavailable)",
            "gpu_name": "N/A",
            "gpu_percent": 0,
            "vram_used_gb": 0,
            "vram_total_gb": 0,
            "vram_percent": 0,
            "temp_c": None,
            "power_w": None,
            **system_stats
        }

    def cleanup(self):
        """Cleanup NVML resources"""
        if self.available:
            try:
                import pynvml
                pynvml.nvmlShutdown()
                logger.info("NVML shutdown complete")
            except Exception as e:
                logger.error(f"Error during NVML cleanup: {e}")


class JetsonOrinMonitor(GPUMonitor):
    """Jetson Orin GPU monitoring using tegrastats or /proc"""

    def __init__(self, history_size: int = 60):
        super().__init__(history_size)
        # TODO: Implement Jetson Orin monitoring
        logger.info("Jetson Orin monitoring not yet implemented")

    def get_stats(self) -> Dict:
        """Get current GPU stats for Jetson Orin"""
        # TODO: Parse tegrastats or /proc data
        system_stats = self.get_cpu_ram_stats()
        return {
            "platform": "Jetson Orin (tegrastats)",
            "gpu_name": "Jetson Orin",
            "gpu_percent": 0,
            "vram_used_gb": 0,
            "vram_total_gb": 0,
            "vram_percent": 0,
            **system_stats
        }

    def cleanup(self):
        """Cleanup resources"""
        pass


def create_monitor(platform: Optional[str] = None) -> GPUMonitor:
    """
    Factory function to create appropriate GPU monitor

    Args:
        platform: Force specific platform ('nvidia', 'jetson_orin', etc.)
                 If None, auto-detect

    Returns:
        Appropriate GPUMonitor instance
    """
    if platform == "nvidia" or platform is None:
        # Try NVML first (works for Desktop, DGX, Jetson Thor)
        try:
            import pynvml
            pynvml.nvmlInit()
            pynvml.nvmlShutdown()
            logger.info("Auto-detected NVIDIA GPU (NVML available)")
            return NVMLMonitor()
        except:
            pass

    if platform == "jetson_orin":
        return JetsonOrinMonitor()

    # Fallback to NVML (will show unavailable)
    logger.warning("No GPU detected, using fallback monitor")
    return NVMLMonitor()

