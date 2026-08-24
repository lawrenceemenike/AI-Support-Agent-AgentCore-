"""
Customer Support AI Agent — Completed Implementation
====================================================
A fully functional customer support AI agent for an e-commerce platform
using Amazon Bedrock AgentCore and the Strands SDK.
"""

# ── Imports ───────────────────────────────────────────────────────────────────
# These imports are provided. Do not remove them.
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Dict
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ── TODO 1 — App Initialisation ───────────────────────────────────────────────
# Create a BedrockAgentCoreApp instance.
# This registers the ASGI server for AgentCore deployment.
# There must be exactly one instance per deployment.

app = BedrockAgentCoreApp()


# Suppress interactive tool-consent prompts (required in headless deployments).
os.environ["BYPASS_TOOL_CONSENT"] = "true"


# ── TODO 2 — Configuration ────────────────────────────────────────────────────
# Replace the placeholder strings with your actual AWS resource values.

GATEWAY_URL = "https://customersupportgateway-ficlwnwjtk.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
KB_ID       = "CSAIKB0001"
REGION      = "us-east-1"
MEMORY_ID   = "CustomerSupportMemory-7gBufM9tWh"


# ── TODO 3 — Model and Clients ────────────────────────────────────────────────
# Create:
#   1. A BedrockModel using model_id "global.amazon.nova-2-lite-v1:0"
#   2. A MemoryClient with region_name=REGION
#   3. A boto3 client for the "bedrock-agent-runtime" service in REGION

model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id=model_id)

memory_client = MemoryClient(region_name=REGION)

_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


# ── TODO 4 — Namespace Helper ─────────────────────────────────────────────────
# Implement get_namespaces() to return a dict mapping strategy type to
# namespace template string.

def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type → namespace template string."""
    try:
        strategies = mem_client.get_memory_strategies(memory_id)
        namespaces = {}
        for strategy in strategies:
            strat_type = strategy.get("type") or strategy.get("memoryStrategyType", "")
            ns_list = strategy.get("namespaceTemplates") or strategy.get("namespaces", [])
            if strat_type and ns_list:
                namespaces[strat_type] = ns_list[0]
        if namespaces:
            return namespaces
    except Exception as e:
        logger.warning(f"Could not retrieve memory strategies: {e}")

    # Fallback to configured default namespace templates
    return {
        "SEMANTIC": "cs_agent/{actorId}/facts",
        "USER_PREFERENCE": "cs_agent/{actorId}/preferences",
    }


# ── TODO 5 — Memory Hook ──────────────────────────────────────────────────────
# Implement MemoryHook, a HookProvider subclass that adds long-term memory.

class MemoryHook(HookProvider):
    """Long-term memory hook for the customer support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(self.memory_client, self.memory_id)

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve relevant memories and prepend them to the user message."""
        if not event.agent or not event.agent.messages:
            return

        last_msg = event.agent.messages[-1]
        # Only run for plain-text user messages (not tool results)
        role = last_msg.get("role") if isinstance(last_msg, dict) else getattr(last_msg, "role", "")
        if role != "user":
            return

        content = last_msg.get("content") if isinstance(last_msg, dict) else getattr(last_msg, "content", [])
        
        # Check if this contains tool results
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and ("tool_result" in block or "toolResult" in block):
                    return

        # Extract user query text
        user_query = ""
        if isinstance(content, str):
            user_query = content
        elif isinstance(content, list):
            texts = [b.get("text", "") for b in content if isinstance(b, dict) and "text" in b]
            user_query = " ".join(texts)

        if not user_query.strip():
            return

        # Query each strategy namespace
        collected_memories = []
        for strategy_type, ns_template in self.namespaces.items():
            formatted_ns = ns_template.format(actorId=self.actor_id)
            try:
                records = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    namespace=formatted_ns,
                    query=user_query,
                    top_k=5,
                )
                for rec in records:
                    rec_content = rec.get("content")
                    mem_text = ""
                    if isinstance(rec_content, dict):
                        mem_text = rec_content.get("text", "")
                    elif isinstance(rec_content, str):
                        mem_text = rec_content
                    if mem_text:
                        collected_memories.append(f"[{strategy_type}] {mem_text.strip()}")
            except Exception as e:
                logger.warning(f"Error retrieving memories for namespace {formatted_ns}: {e}")

        # Prepend retrieved context to the user message
        if collected_memories:
            context_prefix = "Customer Context:\n" + "\n".join(collected_memories)
            if isinstance(content, str):
                if isinstance(last_msg, dict):
                    last_msg["content"] = f"{context_prefix}\n\n{content}"
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        block["text"] = f"{context_prefix}\n\n{block['text']}"
                        break

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds."""
        if not event.agent or not event.agent.messages:
            return

        messages = event.agent.messages
        last_user_query = None
        last_assistant_response = None

        # Walk backwards to find the last assistant message and last plain-text user message
        for msg in reversed(messages):
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", [])

            if role == "assistant" and last_assistant_response is None:
                if isinstance(content, str):
                    last_assistant_response = content
                elif isinstance(content, list):
                    texts = [b.get("text", "") for b in content if isinstance(b, dict) and "text" in b]
                    if texts:
                        last_assistant_response = " ".join(texts)

            elif role == "user" and last_user_query is None:
                is_tool_result = False
                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and ("tool_result" in b or "toolResult" in b):
                            is_tool_result = True
                            break
                if not is_tool_result:
                    if isinstance(content, str):
                        last_user_query = content
                    elif isinstance(content, list):
                        texts = [b.get("text", "") for b in content if isinstance(b, dict) and "text" in b]
                        if texts:
                            raw_text = " ".join(texts)
                            # Strip prepended customer context if present
                            if "Customer Context:\n" in raw_text and "\n\n" in raw_text:
                                raw_text = raw_text.split("\n\n", 1)[1]
                            last_user_query = raw_text

            if last_user_query is not None and last_assistant_response is not None:
                break

        if last_user_query and last_assistant_response:
            try:
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=[
                        (last_user_query, "USER"),
                        (last_assistant_response, "ASSISTANT"),
                    ],
                )
            except Exception as e:
                logger.warning(f"Error saving support interaction to memory: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        """Register both memory callbacks."""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)


# ── TODO 6 — Knowledge Base Tool ─────────────────────────────────────────────
# Implement search_knowledge_base(query) using the @tool decorator.

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty
    information, loyalty program details, and order status definitions.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """
    # 1. If Bedrock Knowledge Base is configured, query it
    if KB_ID and not KB_ID.startswith("<") and KB_ID != "":
        try:
            response = _bedrock_runtime.retrieve(
                knowledgeBaseId=KB_ID,
                retrievalQuery={"text": query},
            )
            results = response.get("retrievalResults", [])
            if results:
                chunks = []
                for r in results:
                    content = r.get("content", {})
                    text = content.get("text", "")
                    if text:
                        chunks.append(text.strip())
                if chunks:
                    return "\n---\n".join(chunks)
        except Exception as e:
            logger.warning(f"Bedrock Knowledge base retrieval failed: {e}")

    # 2. Fallback to product_catalog.txt
    catalog_paths = [
        "product_catalog.txt",
        os.path.join(os.path.dirname(__file__), "product_catalog.txt"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "starter", "product_catalog.txt"),
    ]
    for cp in catalog_paths:
        if os.path.exists(cp):
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    catalog_text = f.read()
                # Return relevant sections based on query keywords
                q_lower = query.lower()
                sections = catalog_text.split("================================================================================")
                matching = []
                for s in sections:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    s_lower = s_clean.lower()
                    words = [w for w in q_lower.split() if len(w) > 3]
                    if any(w in s_lower for w in words):
                        matching.append(s_clean)
                if matching:
                    return "\n---\n".join(matching)
                return catalog_text[:2000]
            except Exception as ex:
                logger.warning(f"Error reading local product catalog: {ex}")

    return "No relevant information found in the knowledge base."


# ── TODO 7 — Loyalty Discount Tool (Code Interpreter) ────────────────────────
# Implement calculate_loyalty_discount() using the @tool decorator.

@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the loyalty discount for a customer order using the
    AgentCore Code Interpreter. Runs exact arithmetic in a secure sandbox.

    Args:
        loyalty_points:   Customer's current points balance
        tier:             Customer tier — Silver, Gold, or Platinum
        order_total:      Order total in USD
        product_category: standard, device, or fresh

    Returns:
        Full discount breakdown and final price
    """
    code = f"""
import json

loyalty_points = {loyalty_points}
tier = "{tier}"
order_total = {order_total}
product_category = "{product_category}"

earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

tier_rate = tier_rates.get(tier, 0.0)
earn_rate = earn_rates.get(product_category.lower(), 1)

# Minimum redemption is 500 points, floored to nearest 500
# Capped at 50% of the order total (100 points = $1)
max_discount_from_pts = order_total * 0.50
max_pts_for_order = int(max_discount_from_pts * 100)

available_redeemable = (loyalty_points // 500) * 500
max_allowed_redeemable = (max_pts_for_order // 500) * 500

points_redeemed = min(available_redeemable, max_allowed_redeemable) if loyalty_points >= 500 else 0
points_discount = round(points_redeemed / 100.0, 2)

subtotal_after_points = max(0.0, order_total - points_discount)
tier_discount = round(subtotal_after_points * tier_rate, 2)
final_total = round(subtotal_after_points - tier_discount, 2)
total_savings = round(points_discount + tier_discount, 2)
points_earned = int(final_total * earn_rate)
remaining_points = loyalty_points - points_redeemed + points_earned

result = {{
    "points_redeemed": points_redeemed,
    "points_discount": points_discount,
    "tier_discount_pct": int(tier_rate * 100),
    "tier_discount": tier_discount,
    "order_total": order_total,
    "final_total": final_total,
    "total_savings": total_savings,
    "points_earned": points_earned,
    "remaining_points": remaining_points,
}}
print(json.dumps(result))
"""

    try:
        with code_session(REGION) as session:
            response = session.invoke(
                "executeCode",
                {
                    "code": code,
                    "language": "python",
                    "clearContext": True,
                },
            )
            for event in response.get("stream", []):
                if "result" in event:
                    result_data = event["result"]
                    content_blocks = result_data.get("content", [])
                    for block in content_blocks:
                        if isinstance(block, dict) and "text" in block:
                            return block["text"].strip()
                    return json.dumps(result_data)

        raise RuntimeError("No result event found in code interpreter response stream")

    except Exception as e:
        logger.warning(f"Code interpreter invocation failed, applying fallback: {e}")
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
        tier_rate = tier_rates.get(tier, 0.0)
        tier_discount = round(order_total * tier_rate, 2)
        final_total = round(order_total - tier_discount, 2)
        fallback_result = {
            "points_redeemed": 0,
            "tier_discount_pct": int(tier_rate * 100),
            "final_total": final_total,
            "remaining_points": loyalty_points,
            "note": "Calculated with tier discount only (code interpreter fallback)",
        }
        return json.dumps(fallback_result)


# ── TODO 8 — Agent Entrypoint ─────────────────────────────────────────────────
# Implement the invoke() function decorated with @app.entrypoint.

@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) — the customer's message
      customer_id (str, optional) — unique customer identifier
      session_id  (str, optional) — session identifier; generated if absent
    """
    try:
        user_input = payload.get("prompt", "")
        actor_id = payload.get("customer_id", "default_customer")
        session_id = payload.get("session_id", str(uuid.uuid4()))

        # Instantiate MemoryHook for this actor/session
        memory_hook = MemoryHook(
            actor_id=actor_id,
            session_id=session_id,
            memory_client=memory_client,
            memory_id=MEMORY_ID,
        )

        # Instantiate AgentCoreBrowser
        agent_core_browser = AgentCoreBrowser(region=REGION)

        # Base tools
        tools = [
            search_knowledge_base,
            calculate_loyalty_discount,
            agent_core_browser.browser,
        ]

        # Load Gateway tools via MCPClient
        if GATEWAY_URL and not GATEWAY_URL.startswith("<"):
            try:
                mcp_client = MCPClient(lambda: streamable_http_client(GATEWAY_URL))
                gateway_tools = await mcp_client.load_tools()
                tools.extend(gateway_tools)
            except Exception as e:
                logger.warning(f"Could not load tools from MCP Gateway: {e}")

        # Retrieve persistent customer context from memory if available
        customer_context_lines = []
        if MEMORY_ID and actor_id:
            try:
                namespaces = get_namespaces(memory_client, MEMORY_ID)
                for stype, ns_template in namespaces.items():
                    ns = ns_template.format(actorId=actor_id)
                    records = memory_client.retrieve_memories(
                        memory_id=MEMORY_ID,
                        actor_id=actor_id,
                        namespace=ns,
                        query=user_input or "customer preference details",
                        top_k=5,
                    )
                    for rec in records:
                        rec_content = rec.get("content", {})
                        text = rec_content.get("text", "") if isinstance(rec_content, dict) else str(rec_content)
                        if text:
                            customer_context_lines.append(f"- [{stype}] {text.strip()}")
            except Exception as e:
                logger.warning(f"Error pre-fetching customer memories: {e}")

        system_prompt = (
            "You are a helpful and intelligent customer support assistant for an e-commerce platform. "
            "You assist customers with order tracking, return processing, product information, "
            "and loyalty rewards calculations. Always provide accurate, concise, and polite responses. "
            "Use the provided tools whenever specific product, order, refund, loyalty, or web data is needed."
        )
        if customer_context_lines:
            system_prompt += (
                "\n\nCustomer Context (from previous sessions with this customer):\n"
                + "\n".join(customer_context_lines)
                + "\nAcknowledge and respect the customer's known preferences and name."
            )

        agent = Agent(
            model=model,
            tools=tools,
            hooks=[memory_hook],
            system_prompt=system_prompt,
        )

        response = await agent.invoke_async(user_input)

        if hasattr(response, "message") and response.message:
            content = response.message.get("content", [])
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    return block["text"]
                elif hasattr(block, "text"):
                    return block.text
        return str(response)

    except Exception as e:
        logger.error(f"Error in invoke: {e}", exc_info=True)
        return f"An error occurred while processing your request: {str(e)}"


# ── CLI entry point (Local Testing & Cloud Runtime) ───────────────────────────
def main():
    """
    Run one invocation from the command line for local CLI testing.
    Usage for local testing:
        uv run python -c 'import asyncio, json, main; print(asyncio.run(main.invoke({"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123"})))'
        OR uncomment `main()` below and run:
        uv run python main.py '{"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123"}'
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    # Production Cloud Runtime Entry Point:
    # `app.run()` starts the Bedrock AgentCore HTTP runtime server listening on container port 8080.
    app.run()
    
    # For local CLI debugging without starting the web server, uncomment the line below:
    # main()
