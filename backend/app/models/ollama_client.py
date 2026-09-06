import base64
import os
from typing import Optional
import httpx

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

class OllamaConnectionError(RuntimeError):
    """Raised when Ollama local service cannot be reached."""
    pass

class OllamaTimeoutError(RuntimeError):
    """Raised when Ollama local service times out during generation."""
    pass

async def generate_text(
    prompt: str,
    system: Optional[str] = None,
    model: str = "qwen2.5:3b",
    timeout_seconds: float = 180.0,
    temperature: Optional[float] = None,
    options: Optional[dict] = None
) -> str:
    """
    Generate text using local Ollama model.
    Strictly restricted to localhost:11434 with defensive connection & timeout error handling.
    """
    req_options = {}
    if options:
        req_options.update(options)
    if temperature is not None:
        req_options["temperature"] = float(temperature)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m"
    }
    if req_options:
        payload["options"] = req_options
    if system:
        payload["system"] = system

    timeout = httpx.Timeout(timeout_seconds, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
        raise OllamaConnectionError("Local model unavailable — check Ollama is running") from conn_err
    except httpx.TimeoutException as time_err:
        raise OllamaTimeoutError(f"Local model request timed out after {int(timeout_seconds)}s") from time_err
    except httpx.HTTPStatusError as http_err:
        raise RuntimeError(f"Local Ollama returned HTTP {http_err.response.status_code}: {http_err.response.text}") from http_err
    except Exception as e:
        if "connect" in str(e).lower() or "11434" in str(e):
            raise OllamaConnectionError("Local model unavailable — check Ollama is running") from e
        raise

async def generate_vision(
    prompt: str,
    image_path: str,
    model: str = "qwen2.5vl:7b",
    timeout_seconds: float = 300.0
) -> str:
    """
    Perform multimodal/OCR generation using local Ollama vision model.
    Strictly restricted to localhost:11434 with defensive connection & timeout error handling.
    """
    # Optimize image resolution for vision model token budget if necessary
    from PIL import Image
    import io
    try:
        with Image.open(image_path) as pil_img:
            if max(pil_img.size) > 1024:
                pil_img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=90)
                encoded_image = base64.b64encode(buf.getvalue()).decode("utf-8")
            else:
                with open(image_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [encoded_image],
        "options": {"num_ctx": 8192},
        "stream": False,
        "keep_alive": "10m"
    }

    timeout = httpx.Timeout(timeout_seconds, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
        raise OllamaConnectionError("Local model unavailable — check Ollama is running") from conn_err
    except httpx.TimeoutException as time_err:
        raise OllamaTimeoutError(f"Local vision model request timed out after {int(timeout_seconds)}s") from time_err
    except httpx.HTTPStatusError as http_err:
        raise RuntimeError(f"Local Ollama returned HTTP {http_err.response.status_code}: {http_err.response.text}") from http_err
    except Exception as e:
        if "connect" in str(e).lower() or "11434" in str(e):
            raise OllamaConnectionError("Local model unavailable — check Ollama is running") from e
        raise
