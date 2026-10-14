"""Conservative, read-only capacity estimates from completed plug-in sessions."""
from __future__ import annotations

import math
from statistics import median, pstdev


class BatteryHealth:
    """Never infer efficiency and capacity from the same observation."""

    def __init__(self):
        self.samples = []
        self.context = None
        self.active = None
        self.blocked = False
        self.reason = "collecting"

    def restore(self, data, context):
        self.context = context
        if not isinstance(data, dict) or data.get("context") != context:
            return
        values = data.get("samples", [])
        if isinstance(values, list):
            self.samples = [float(v) for v in values if isinstance(v, (int, float))
                            and math.isfinite(v) and context[0] * .4 <= v <= context[0] * 1.2][-20:]

    def export(self):
        # In-progress sessions are intentionally not restored across data gaps.
        return {"context": self.context, "samples": self.samples}

    @property
    def capacity(self):
        return median(self.samples) if len(self.samples) >= 3 else None

    @property
    def spread(self):
        return 100 * pstdev(self.samples) / median(self.samples) if len(self.samples) >= 2 else None

    @property
    def quality(self):
        if len(self.samples) < 3:
            return "collecting"
        if len(self.samples) >= 5 and self.spread <= 5:
            return "consistent_estimate"
        return "provisional_estimate"

    def observe(self, connected, soc, energy, context):
        """Return True when persisted history changes; pauses keep one session."""
        changed = False
        if context != self.context:
            self.context = context
            self.samples = []
            self.active = None
            self.blocked = False
            changed = True
        nominal, efficiency, *_ = context
        if connected is False:
            if self.active and not self.blocked:
                start_soc, start_energy, end_soc, end_energy = self.active
                delta = end_soc - start_soc
                if delta >= 30 and end_energy > start_energy:
                    capacity = (end_energy - start_energy) * efficiency / delta
                    if nominal * .4 <= capacity <= nominal * 1.2:
                        self.samples = (self.samples + [capacity])[-20:]
                        self.reason = "accepted"
                        changed = True
                    else:
                        self.reason = "implausible_capacity"
                else:
                    self.reason = "soc_span_too_small"
            self.active = None
            self.blocked = False
            return changed
        valid = (connected is True and soc is not None and energy is not None
                 and math.isfinite(soc) and 0 <= soc <= 100
                 and math.isfinite(energy) and energy >= 0
                 and math.isfinite(nominal) and nominal > 0
                 and math.isfinite(efficiency) and 0 < efficiency <= 100)
        if not valid:
            if self.active:
                self.blocked = True
            self.active = None
            self.reason = "source_data_unavailable"
            return changed
        if self.blocked:
            return changed
        if self.active is None:
            self.active = (soc, energy, soc, energy)
            self.reason = "session_in_progress"
        else:
            start_soc, start_energy, last_soc, last_energy = self.active
            if energy < last_energy or soc < last_soc:
                self.active = None
                self.blocked = True
                self.reason = "counter_reset_or_soc_decreased"
            else:
                self.active = (start_soc, start_energy, soc, energy)
        return changed
