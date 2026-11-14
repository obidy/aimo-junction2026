import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI(title="Valio Aimo Vapi Voice Bridge")

# Connects to your existing gateway running in aimo_api.py
AIMO_GATEWAY_URL = os.environ.get("AIMO_GATEWAY_URL", "http://127.0.0.1:8000")
AIMO_AGENT_TOKEN = os.environ.get("AIMO_AGENT_TOKEN", "")

@app.post("/vapi-webhook")
async def handle_vapi_tool_calls(request: Request):
    payload = await request.json()
    message = payload.get("message", {})

    # Vapi sends 'tool-calls' when the voice assistant triggers a function
    if message.get("type") == "tool-calls":
        results = []
        headers = {"Authorization": f"Bearer {AIMO_AGENT_TOKEN}"} if AIMO_AGENT_TOKEN else {}

        async with httpx.AsyncClient(base_url=AIMO_GATEWAY_URL, timeout=60.0) as client:
            for call in message.get("toolCalls", []):
                tool_id = call.get("id")
                fn = call.get("function", {})
                fn_name = fn.get("name")
                args = fn.get("arguments", {})

                # Route 1: Voice request for a meal plan / recipe basket (matches recipe_client.py)
                if fn_name == "create_recipe_plan":
                    res = await client.post(
                        "/recipe-plans",
                        headers=headers,
                        json={
                            "request": args.get("request", ""),
                            "portions": int(args.get("portions", 100)),
                            "delivery_date": args.get("delivery_date", "2026-11-16"),
                            "preferences": args.get("preferences", ""),
                            "autonomy": "automatic" if args.get("auto_commit") else "review",
                            "auto_commit": bool(args.get("auto_commit", False)),
                        },
                    )
                    data = res.json()
                    spoken_summary = (
                        f"Recipe plan {data.get('id')} for {data.get('recipe', {}).get('title')} "
                        f"is {data.get('status')}. Total is {data.get('total_gross_eur')} euros."
                    )
                    results.append({"toolCallId": tool_id, "result": spoken_summary})

                # Route 2: Direct product/milk comparison lookup
                elif fn_name == "search_products":
                    res = await client.get(
                        "/products",
                        headers=headers,
                        params={"q": args.get("query", "")},
                    )
                    results.append({"toolCallId": tool_id, "result": str(res.json()[:3])})

        return {"results": results}

    return {"status": "ok"}