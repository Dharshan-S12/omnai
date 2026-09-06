import sys
import os
import uuid
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import MemoryEntry
from app.memory.retrieve import compute_strength

def test_memory_decay_safety_critical():
    print("=" * 70)
    print("   TEST: Long-Term Memory Safety Decay Gating (0-Decay for Violations)")
    print("=" * 70)

    simulated_past_date = datetime.utcnow() - timedelta(days=180)  # 6 months ago

    # 1. Safety-Critical Memory (e.g. Zone D Critical Emergency Shutdown reading on TRB-1105)
    critical_entry = MemoryEntry(
        id=uuid.uuid4(),
        entity_key="equipment_id:TRB-1105",
        summary_text="Emergency Shutdown: Vibration velocity RMS reached 8.2 mm/s (Zone D Violation).",
        strength_score=1.0,
        safety_critical=True,
        created_at=simulated_past_date,
        last_accessed_at=simulated_past_date,
        access_count=0
    )

    # 2. General Conversational / Contextual Memory (e.g. Casual operator note)
    casual_entry = MemoryEntry(
        id=uuid.uuid4(),
        entity_key="entity:general_chat",
        summary_text="Operator mentioned shift handover completed smoothly.",
        strength_score=1.0,
        safety_critical=False,
        created_at=simulated_past_date,
        last_accessed_at=simulated_past_date,
        access_count=0
    )

    strength_critical = compute_strength(critical_entry)
    strength_casual = compute_strength(casual_entry)

    print(f" -> 6-Month-Old Safety-Critical Reading Strength: {strength_critical:.4f} (Exempt from Decay: {critical_entry.safety_critical})")
    print(f" -> 6-Month-Old Casual Note Strength:           {strength_casual:.4f} (Normal Ebbinghaus Decay)")

    # Assertions
    assert strength_critical == 1.0, f"Safety critical memory must retain 100% strength (1.0), got {strength_critical}"
    assert strength_casual < 0.05, f"Casual memory after 180 days must decay significantly (<0.05), got {strength_casual}"
    print(f" -> Retention Ratio (Critical / Casual): {strength_critical / strength_casual:.1f}x higher retention")

    print("\n[PASS] Safety-critical memories retain 100% retention over time while casual context decays gracefully!")
    print("=" * 70)

if __name__ == "__main__":
    test_memory_decay_safety_critical()
