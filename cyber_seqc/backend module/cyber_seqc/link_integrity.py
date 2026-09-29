"""
Link Integrity
================
Monitors the health and authenticity of the satellite/RF link itself.
Encryption (advanced_cryptography.py) protects data CONTENT; this module
protects the data PATH -- detecting jamming, spoofed transmitters, and
degraded link quality so operators/other modules can react (failover,
alerts) before a disaster-response message is lost or faked.

In this hackathon prototype, live RF hardware isn't available, so
`SignalTelemetry` simulates realistic readings. Swap `read_live_sample()`
for a real modem/SDR feed later -- the detection logic itself is real.

Contains:
    - SignalTelemetry     : one snapshot of RF link conditions
    - AntiJammingDetector : flags jamming from abnormal SNR/noise-floor
    - AntiSpoofingVerifier: HMAC-based beacon authentication
    - VSATMonitor         : tracks the ~4 MHz VSAT channel over time
    - RFLinkReliability   : uptime / latency / packet-loss tracking
"""

from __future__ import annotations

import hashlib
import hmac
import random
import time
from collections import deque
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Telemetry snapshot
# ---------------------------------------------------------------------------

@dataclass
class SignalTelemetry:
    timestamp: float
    frequency_mhz: float      # nominal centre frequency within the 4 MHz VSAT band
    snr_db: float             # signal-to-noise ratio
    bit_error_rate: float
    latency_ms: float
    packet_loss_pct: float


def read_live_sample(center_freq_mhz: float = 4000.0, jam_probability: float = 0.05) -> SignalTelemetry:
    """
    SIMULATED sensor read. Replace with a real modem/SDR API call in
    production. Occasionally injects a "jammed"-looking sample so the
    detector logic below has something realistic to catch.
    """
    jammed = random.random() < jam_probability
    return SignalTelemetry(
        timestamp=time.time(),
        frequency_mhz=center_freq_mhz + random.uniform(-0.05, 0.05),
        snr_db=random.uniform(2, 6) if jammed else random.uniform(12, 22),
        bit_error_rate=random.uniform(1e-2, 1e-1) if jammed else random.uniform(1e-7, 1e-5),
        latency_ms=random.uniform(550, 620),        # typical GEO VSAT round-trip
        packet_loss_pct=random.uniform(5, 25) if jammed else random.uniform(0, 1.5),
    )


# ---------------------------------------------------------------------------
# 1. Anti-Jamming & Anti-Spoofing
# ---------------------------------------------------------------------------

class AntiJammingDetector:
    """
    Flags jamming using threshold rules on SNR / bit-error-rate -- a
    sudden SNR collapse or BER spike is the classic signature of an
    intentional or environmental jamming event.

    Example
    -------
    >>> detector = AntiJammingDetector()
    >>> sample = SignalTelemetry(time.time(), 4000.0, snr_db=3.0, bit_error_rate=0.05,
    ...                           latency_ms=600, packet_loss_pct=20)
    >>> detector.is_jammed(sample)
    True
    """

    def __init__(self, snr_floor_db: float = 8.0, ber_ceiling: float = 1e-3) -> None:
        self.snr_floor_db = snr_floor_db
        self.ber_ceiling = ber_ceiling

    def is_jammed(self, sample: SignalTelemetry) -> bool:
        return sample.snr_db < self.snr_floor_db or sample.bit_error_rate > self.ber_ceiling


class AntiSpoofingVerifier:
    """
    Verifies that an incoming beacon/status signal genuinely originates
    from the real station (or real control room) using an HMAC beacon
    signature, so an attacker can't impersonate the station and inject
    a fake "all systems normal" message during a real emergency.

    Example
    -------
    >>> verifier = AntiSpoofingVerifier(shared_key=b"beacon-preshared-key")
    >>> beacon = verifier.sign_beacon("STATION_MAITRI_OK")
    >>> verifier.verify_beacon(beacon)
    True
    >>> tampered = {**beacon, "payload": "STATION_MAITRI_EVACUATE"}
    >>> verifier.verify_beacon(tampered)
    False
    """

    def __init__(self, shared_key: bytes) -> None:
        self._key = shared_key

    def sign_beacon(self, payload: str) -> dict:
        sig = hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()
        return {"payload": payload, "signature": sig}

    def verify_beacon(self, beacon: dict) -> bool:
        expected = hmac.new(self._key, beacon["payload"].encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, beacon["signature"])


# ---------------------------------------------------------------------------
# 2. VSAT Monitoring (4 MHz band)
# ---------------------------------------------------------------------------

class VSATMonitor:
    """
    Continuously tracks the VSAT channel's key parameters within its
    allocated ~4 MHz band and keeps a rolling history for dashboards/alerts.

    Example
    -------
    >>> monitor = VSATMonitor(band_center_mhz=4000.0, band_width_mhz=4.0)
    >>> status = monitor.poll()
    >>> "within_band" in status
    True
    """

    def __init__(self, band_center_mhz: float = 4000.0, band_width_mhz: float = 4.0, history_size: int = 50) -> None:
        self.band_center_mhz = band_center_mhz
        self.band_width_mhz = band_width_mhz
        self._jam_detector = AntiJammingDetector()
        self.history: deque[SignalTelemetry] = deque(maxlen=history_size)

    def poll(self) -> dict:
        sample = read_live_sample(center_freq_mhz=self.band_center_mhz)
        self.history.append(sample)
        half_band = self.band_width_mhz / 2
        within_band = abs(sample.frequency_mhz - self.band_center_mhz) <= half_band
        return {
            "timestamp": sample.timestamp,
            "frequency_mhz": round(sample.frequency_mhz, 4),
            "within_band": within_band,
            "snr_db": round(sample.snr_db, 2),
            "bit_error_rate": sample.bit_error_rate,
            "jammed_suspected": self._jam_detector.is_jammed(sample),
        }

    def recent_average_snr(self) -> float | None:
        if not self.history:
            return None
        return sum(s.snr_db for s in self.history) / len(self.history)


# ---------------------------------------------------------------------------
# 3. RF Link Reliability
# ---------------------------------------------------------------------------

class RFLinkReliability:
    """
    Tracks link reliability over time (uptime %, average latency, packet
    loss) and raises a failover-worthy alert when reliability degrades
    below a configurable threshold -- important because disaster-response
    messages need a guaranteed communication path.

    Example
    -------
    >>> reliability = RFLinkReliability()
    >>> for _ in range(20):
    ...     _ = reliability.record(read_live_sample())
    >>> report = reliability.report()
    >>> "uptime_pct" in report
    True
    """

    def __init__(self, packet_loss_outage_threshold_pct: float = 10.0, min_uptime_pct: float = 95.0) -> None:
        self.packet_loss_outage_threshold_pct = packet_loss_outage_threshold_pct
        self.min_uptime_pct = min_uptime_pct
        self._samples: list[SignalTelemetry] = []

    def record(self, sample: SignalTelemetry) -> bool:
        """Records a sample; returns True if this sample counts as link 'up'."""
        self._samples.append(sample)
        return sample.packet_loss_pct < self.packet_loss_outage_threshold_pct

    def report(self) -> dict:
        if not self._samples:
            return {"uptime_pct": None, "avg_latency_ms": None, "avg_packet_loss_pct": None, "alert": False}
        up_count = sum(1 for s in self._samples if s.packet_loss_pct < self.packet_loss_outage_threshold_pct)
        uptime_pct = 100 * up_count / len(self._samples)
        avg_latency = sum(s.latency_ms for s in self._samples) / len(self._samples)
        avg_loss = sum(s.packet_loss_pct for s in self._samples) / len(self._samples)
        return {
            "uptime_pct": round(uptime_pct, 2),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_packet_loss_pct": round(avg_loss, 2),
            "alert": uptime_pct < self.min_uptime_pct,
        }
