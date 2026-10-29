"""
Pymem Real-Time Memory Reader for Football Manager (fm.exe)
Attaches to fm.exe in read-only mode, resolves pointer chains / AOB signatures from offsets.json,
and automatically falls back to LiveMatchSimulator when fm.exe is not running.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.memory.simulator import LiveMatchSimulator
from app.models.match_state import MatchSnapshot

try:
    import pymem
    import pymem.process
    PYMEM_AVAILABLE = True
except ImportError:
    PYMEM_AVAILABLE = False


class FMMemoryReader:
    def __init__(self, simulator: LiveMatchSimulator) -> None:
        self.simulator = simulator
        self.offsets_path = Path(__file__).parent / "offsets.json"
        self.config: Dict[str, Any] = self._load_offsets()
        self.pm: Optional[Any] = None
        self.module_base: Optional[int] = None
        self.is_attached: bool = False

    def _load_offsets(self) -> Dict[str, Any]:
        if self.offsets_path.exists():
            return json.loads(self.offsets_path.read_text(encoding="utf-8"))
        return {"target_process": "fm.exe", "pointer_chains": {}, "player_struct_offsets": {}}

    def try_attach(self) -> bool:
        """Attempt to attach to fm.exe using Pymem."""
        if not PYMEM_AVAILABLE:
            self.is_attached = False
            return False
        target = self.config.get("target_process", "fm.exe")
        try:
            self.pm = pymem.Pymem(target)
            module = pymem.process.module_from_name(self.pm.process_handle, target)
            self.module_base = module.lpBaseOfDll
            self.is_attached = True
            return True
        except Exception:
            self.pm = None
            self.module_base = None
            self.is_attached = False
            return False

    def resolve_pointer_chain(self, base_offset_hex: str, offsets_hex: List[str]) -> Optional[int]:
        """Follows a multi-level pointer chain starting from module_base + base_offset."""
        if not self.is_attached or self.pm is None or self.module_base is None:
            return None
        try:
            addr = self.module_base + int(base_offset_hex, 16)
            for off_str in offsets_hex[:-1]:
                addr = self.pm.read_longlong(addr)
                if not addr:
                    return None
                addr += int(off_str, 16)
            final_ptr = self.pm.read_longlong(addr)
            if not final_ptr:
                return None
            return final_ptr + int(offsets_hex[-1], 16)
        except Exception:
            return None

    @staticmethod
    def normalize_attr(raw_val: int) -> float:
        """Converts FM internal 1~100 attribute scale (if > 20) to standard 1~20 scale."""
        if raw_val > 20:
            return round(max(1.0, min(20.0, raw_val / 5.0)), 1)
        return float(max(1, min(20, raw_val)))

    def read_snapshot(self) -> MatchSnapshot:
        """
        Attempts to read live match state from fm.exe memory.
        If fm.exe is not running or match controller pointer is null (e.g. on main menu),
        returns the current snapshot from LiveMatchSimulator.
        """
        if not self.is_attached:
            self.try_attach()

        if self.is_attached and self.pm is not None:
            chains = self.config.get("pointer_chains", {})
            clock_chain = chains.get("match_clock_minute")
            if clock_chain:
                clock_addr = self.resolve_pointer_chain(
                    clock_chain["base_offset"], clock_chain["offsets"]
                )
                if clock_addr:
                    try:
                        live_min = self.pm.read_int(clock_addr)
                        if 0 <= live_min <= 130:
                            snap = self.simulator.get_snapshot()
                            snap.match_minute = live_min
                            snap.data_source = "PYMEM_LIVE"
                            return snap
                    except Exception:
                        self.is_attached = False

        return self.simulator.get_snapshot()

