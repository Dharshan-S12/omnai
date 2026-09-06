# PowerShell script to run all Sovereign Workbench automated tests & hardening verification
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Running MRPL Sovereign Workbench Hardened Test Suite" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$backendDir = "c:\sih117\prototype\backend"
$pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Virtualenv python not found at $pythonExe" -ForegroundColor Red
    exit 1
}

$tests = @(
    # Core Hardening Architecture Tests (Items 1 - 14)
    "scripts/test_rule_config_and_sanitization.py",
    "scripts/test_rule_safety_override_block.py",
    "scripts/test_intent_router_eval.py",
    "scripts/test_ensemble_dissent_logging.py",
    "scripts/test_sandbox_hardening.py",
    "scripts/test_memory_decay_safety.py",
    "scripts/test_audit_hash_chain.py",
    "scripts/scan_airgap_dependencies.py",
    "scripts/test_db_backend_parity.py",
    "scripts/test_docgen_failure_handling.py",
    "scripts/test_ocr_quality_and_confidence.py",
    "scripts/test_predictive_nonlinear_trends.py",
    "scripts/test_cross_doc_citations.py",
    
    # Phase 2 Part A — Security Hardening Suites
    "scripts/test_model_integrity.py",
    "scripts/test_encryption_at_rest.py",
    "scripts/test_auth_enforcement.py",
    "scripts/test_secrets_not_in_plaintext.py",
    "scripts/test_forensic_log_redaction.py",
    "scripts/test_prompt_injection_resistance.py",

    # Phase 2 Part B — Retrieval & Vectorization Performance Suites
    "scripts/test_vector_index_scaling.py",
    "scripts/test_embedding_quantization.py",
    "scripts/test_hybrid_retrieval.py",
    "scripts/test_chunking_integrity.py",
    "scripts/test_cache_correctness.py",
    "scripts/test_batch_ingestion_throughput.py",

    # Baseline Platform Verification
    "scripts/test_rule_engine.py",
    "scripts/test_predictive_trend.py",
    "scripts/test_safety_gate.py",
    "scripts/test_memory_evolution.py",
    "scripts/test_equipment_graph.py",
    "scripts/test_semantic_cache.py",
    "scripts/test_cross_doc_count.py"
)

Set-Location $backendDir

$passedCount = 0
$failedCount = 0
$failedTests = @()

foreach ($test in $tests) {
    Write-Host "`n>>> Running $test ..." -ForegroundColor Yellow
    & $pythonExe $test
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Test failed: $test" -ForegroundColor Red
        $failedCount++
        $failedTests += $test
    } else {
        Write-Host "[PASS] Completed: $test" -ForegroundColor Green
        $passedCount++
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  TEST EXECUTION SUMMARY" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Total Suites Run : $($tests.Length)" -ForegroundColor White
Write-Host "Passed Suites    : $passedCount" -ForegroundColor Green
if ($failedCount -gt 0) {
    Write-Host "Failed Suites    : $failedCount" -ForegroundColor Red
    foreach ($f in $failedTests) {
        Write-Host "  - $f" -ForegroundColor Red
    }
    exit 1
} else {
    Write-Host "Failed Suites    : 0" -ForegroundColor Green
    Write-Host "`n[SUCCESS] ALL 14 ARCHITECTURAL HARDENING REQUIREMENTS VERIFIED!" -ForegroundColor Green
}
Write-Host "==========================================================" -ForegroundColor Cyan
