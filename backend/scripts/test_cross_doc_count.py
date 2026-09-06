import os
import sys
import uuid
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.cross_doc import parse_doc_count, run_cross_doc_query, DEFAULT_DOC_COUNT, MAX_DOC_CAP
from app.database import AsyncSessionLocal, engine, Base
from app.models import Task, TaskStep, TaskStatus, TaskType
from sqlalchemy.future import select

def test_parse_doc_count_unit():
    print("---------------------------------------------------------------------")
    print("   TEST 1: Unit Testing parse_doc_count() Logic                      ")
    print("---------------------------------------------------------------------")

    # 1. Default N (should be 10)
    count, capped, req = parse_doc_count("summarize recent plant maintenance records")
    print(f"Query: 'summarize recent plant maintenance records' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 10, f"Expected 10, got {count}"
    assert capped is False
    assert req is None

    count, capped, req = parse_doc_count("")
    print(f"Query: '' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 10

    # 2. Number parsing override (e.g. "last 3", "past 5", "7 reports")
    count, capped, req = parse_doc_count("summarize the last 3 reports")
    print(f"Query: 'summarize the last 3 reports' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 3, f"Expected 3, got {count}"
    assert capped is False
    assert req == 3

    count, capped, req = parse_doc_count("compare past 5 documents")
    print(f"Query: 'compare past 5 documents' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 5
    assert capped is False
    assert req == 5

    count, capped, req = parse_doc_count("review 8 inspections from last month")
    print(f"Query: 'review 8 inspections from last month' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 8
    assert capped is False
    assert req == 8

    count, capped, req = parse_doc_count("what happened in the last four tasks?")
    print(f"Query: 'what happened in the last four tasks?' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 4
    assert capped is False
    assert req == 4

    # 3. Upper cap enforcement (max 20)
    count, capped, req = parse_doc_count("summarize the last 50 reports")
    print(f"Query: 'summarize the last 50 reports' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 20, f"Expected 20, got {count}"
    assert capped is True, "Expected capped=True"
    assert req == 50

    count, capped, req = parse_doc_count("analyze 1000 tasks across the ledger")
    print(f"Query: 'analyze 1000 tasks across the ledger' -> Count: {count}, Capped: {capped}, Req: {req}")
    assert count == 20
    assert capped is True
    assert req == 1000

    print(" -> All unit tests for parse_doc_count() passed!\n")

async def test_cross_doc_execution():
    print("---------------------------------------------------------------------")
    print("   TEST 2: Integration Testing run_cross_doc_query() Logging         ")
    print("---------------------------------------------------------------------")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Create a cross_doc task with query exceeding cap (e.g. 50 reports)
    task_id = uuid.uuid4()
    query_text = "Summarize the last 50 reports for anomalies"

    async with AsyncSessionLocal() as db:
        t = Task(
            id=task_id,
            task_type=TaskType.cross_doc_query,
            input_ref=query_text,
            status=TaskStatus.pending
        )
        db.add(t)
        await db.commit()

    print(f"Created task {task_id} with query: '{query_text}'")
    await run_cross_doc_query(task_id=task_id, query=query_text)

    # Inspect TaskSteps
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(TaskStep).where(TaskStep.task_id == task_id).order_by(TaskStep.step_number))
        steps = res.scalars().all()

    print("Task Steps Logged:")
    for s in steps:
        print(f" - [{s.tool_called}] {s.description}")
        if s.tool_called in ["cross_doc_fetch", "search_memory"]:
            print(f"   tool_result: {s.tool_result}")
            assert s.tool_result.get("was_capped") is True, "Expected was_capped to be True in tool_result"
            assert s.tool_result.get("cap_limit") == 20
            assert "capped" in s.description.lower(), "Expected capping note in step description"

    # 2. Create a cross_doc task with query specifying 3 reports
    task_id_3 = uuid.uuid4()
    query_3 = "Summarize the last 3 reports"

    async with AsyncSessionLocal() as db:
        t3 = Task(
            id=task_id_3,
            task_type=TaskType.cross_doc_query,
            input_ref=query_3,
            status=TaskStatus.pending
        )
        db.add(t3)
        await db.commit()

    print(f"\nCreated task {task_id_3} with query: '{query_3}'")
    await run_cross_doc_query(task_id=task_id_3, query=query_3)

    async with AsyncSessionLocal() as db:
        res3 = await db.execute(select(TaskStep).where(TaskStep.task_id == task_id_3).order_by(TaskStep.step_number))
        steps3 = res3.scalars().all()

    for s in steps3:
        print(f" - [{s.tool_called}] {s.description}")
        if s.tool_called in ["cross_doc_fetch", "search_memory"]:
            print(f"   tool_result: {s.tool_result}")
            assert s.tool_result.get("target_count", s.tool_result.get("query_count")) == 3
            assert s.tool_result.get("was_capped") is False

    print("\n -> All integration tests passed successfully!")

async def main():
    test_parse_doc_count_unit()
    await test_cross_doc_execution()

if __name__ == "__main__":
    asyncio.run(main())
