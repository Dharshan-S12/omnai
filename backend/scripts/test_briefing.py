import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from app.models.ollama_client import generate_text

prompt = """You are an on-premise sovereign intelligence analyst operating in an air-gapped environment.
The user is asking for the latest recorded news / updates / problems / findings from the local database ledger.

User Query: i need the latest news that have been recorded

Historical Source Tasks from Ledger:
Document #1 [Task ID: 41ee34d2 | Type: ocr | Date: 2026-09-01 18:05:11]:
Equipment: PMP-7001 (Main Pump House Unit 3)
Inspector: E. Sharma, Lead Reliability Engineer
Measurements: Vibration Velocity 2.1 mm/s RMS, Frequency 48 Hz, Oil Cleanliness ISO 16/13 Satisfactory, Seal Temp 65 C
Status: COMPLIANT (Zone A Normal Operating Limits)

Document #2 [Task ID: 2f66a87d | Type: ocr | Date: 2026-09-01 17:59:46]:
Equipment: Centrifugal Pump P-101 (Tag: P-101A)
Inspection Type: Routine Predictive Maintenance
Measurements: Motor Drive End 1.8 mm/s, Motor Non-Drive End 2.1 mm/s, Pump Drive End 1.9 mm/s, Pump Non-Drive End 2.3 mm/s
Status: COMPLIANT (ISO Zone A < 2.8 mm/s)

Document #3 [Task ID: 64148e97 | Type: code_exec | Date: 2026-09-01 17:53:03]:
Calculation: Python verification of vibration amplitude RMS (2.1 mm/s < 2.8 mm/s)
Result: Compliant verified via calculation.

Instructions:
1. Directly present a structured Executive Briefing of the latest recorded activities, status, and findings.
2. Group by date/equipment and highlight status, key metrics, and observations.
3. Do NOT make meta-disclaimers or talk about internet news."""

async def run():
    res = await generate_text(prompt=prompt, model="qwen2.5:3b")
    with open("scripts/test_out.txt", "w", encoding="utf-8") as f:
        f.write(res)
    print("Done generating! Saved to test_out.txt")

if __name__ == "__main__":
    asyncio.run(run())
