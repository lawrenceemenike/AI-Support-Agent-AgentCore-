# Project Submission Deliverable: AI Customer Support Agent with Bedrock AgentCore

**GitHub Repository:** [https://github.com/lawrenceemenike/AI-Support-Agent-AgentCore-](https://github.com/lawrenceemenike/AI-Support-Agent-AgentCore-)

---

## 1. Completed `main.py`
The full implementation is in `starter/main.py`. All 8 TODO sections have been implemented with zero `pass` or `None` placeholders:
- **TODO 1**: `BedrockAgentCoreApp()` initialized at module level.
- **TODO 2**: Configuration constants (`GATEWAY_URL`, `MEMORY_ID`, `REGION`, `KB_ID`).
- **TODO 3**: Model initialized (`BedrockModel("global.amazon.nova-2-lite-v1:0")`).
- **TODO 4**: `get_namespaces()` extracting memory strategy types and namespace templates.
- **TODO 5**: `MemoryHook(HookProvider)` with `retrieve_customer_context` (prepending LTM) and `save_support_interaction` (persisting user/assistant turns).
- **TODO 6**: `search_knowledge_base` RAG tool querying Bedrock Knowledge Base and product catalog.
- **TODO 7**: `calculate_loyalty_discount` sandboxed tool executing arithmetic via `code_session` Code Interpreter.
- **TODO 8**: `@app.entrypoint async def invoke(payload, context=None)` with tool assembly, browser tool, MCP gateway loading, and invocation handler.

---

## 2. Test 1 — Order Tracking (Terminal Output)

**Command:**
```bash
agentcore invoke '{"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123", "session_id": "t1"}'
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: 30e60301-b6e6-4cde-9674-5eb6f3e6f156                               │
│ Request ID: 6dd9bd4b-1a2e-45d6-8b40-aca5d74a40c2                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
I've tracked your order ORD-001 and here's the current status:

Order Status: SHIPPED 🚚
Customer: CUST-123
Items: 
- Wireless Headphones Pro (1 x $89.99)

Total: $89.99
Carrier: UPS
Tracking Number: TRK987654321
Estimated Delivery: August 26, 2026

Your order is currently in transit and expected to be delivered by August 26, 2026. You can track the package using the tracking number TRK987654321 with UPS.
```

---

## 3. Test 2 — Refund Processing (Terminal Output)

**Command:**
```bash
agentcore invoke '{"prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.", "customer_id": "CUST-123", "session_id": "t2"}'
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: 30e60301-b6e6-4cde-9674-5eb6f3e6f156                               │
│ Request ID: cf4d37f8-e6c3-4116-a872-b4ae2283d8fe                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
Perfect! Your refund for the Kindle Paperwhite (ORD-002) has been approved.

- Refund ID: REF-L8OIRM1O  
- Status: APPROVED  
- Amount: $0 (full refund)  
- Credit will appear: In 3-5 business days  

The refund has been processed and you'll see the credit on your original payment method within the next few business days. If you need a prepaid return shipping label for the device, I can help with that as well.
```

---

## 4. Test 3 — Knowledge Base (RAG) (Terminal Output)

**Command:**
```bash
agentcore invoke '{"prompt": "What are the benefits of the Platinum loyalty tier?", "customer_id": "CUST-123", "session_id": "t3"}'
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: 30e60301-b6e6-4cde-9674-5eb6f3e6f156                               │
│ Request ID: e502e1b5-00a9-4c59-bafa-e5f61464c962                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
## Platinum Loyalty Tier Benefits

Based on the Amazon Loyalty Rewards Program information, the Platinum tier offers these exclusive benefits:

### Shipping Benefits
- Free same-day shipping on eligible orders

### Discount Benefits
- 15% discount on purchases (compared to Gold's 10% discount)

### Support Benefits
- Priority customer support for faster assistance

### Tier Requirements
- Requires 5,000 or more loyalty points to reach Platinum status

### Additional Program Details
- Earning points: Standard items (1 pt/$1), Amazon devices (2 pts/$1), Amazon Fresh (5 pts/$1)
- Redeeming points: 100 points equals $1 discount, with a minimum redemption of 500 points
- Points are valid for 2 years from the date earned
```

---

## 5. Test 4 — Long-Term Memory (Both Sessions) (Terminal Output)

### Session A (Introduce Customer and Preferences)
**Command:**
```bash
agentcore invoke '{"prompt": "Hi, I am Jane. I prefer concise responses.", "customer_id": "CUST-123", "session_id": "s-A"}'
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: d420e0ad-810e-4a8b-9ea9-ebd30a30e640                               │
│ Request ID: a51fe412-b9a0-49aa-9553-9970f3dfd99f                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
Hello Jane! I'll keep my responses concise. How can I assist you today?
```

*(Waited 35s for background AgentCore Memory extraction into `customer_facts` and `customer_preferences`)*

### Session B (Verify Cross-Session Memory Recall)
**Command:**
```bash
agentcore invoke '{"prompt": "Do you remember my name and communication preference?", "customer_id": "CUST-123", "session_id": "s-B"}'
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: d420e0ad-810e-4a8b-9ea9-ebd30a30e640                               │
│ Request ID: 856f2e60-f6fb-4099-82e8-e9abeeb102a9                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
Yes, Jane, I remember your name and that you prefer concise responses. How can I assist you today?
```

---

## 6. Test 5 — Loyalty Discount Calculation (Terminal Output)

**Command:**
```bash
agentcore invoke '{"prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.", "customer_id": "CUST-123", "session_id": "t5"}
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: d420e0ad-810e-4a8b-9ea9-ebd30a30e640                               │
│ Request ID: 2e63c525-8a80-43ca-9ba8-98e78b5ee67d                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
Based on your Gold membership and 4,250 loyalty points, your $150 standard order discount breakdown is:

- Points redeemed: 4,000 points ($40 discount)
- Gold tier discount: 10% ($15 discount)
- Total savings: $55
- Final total: $95

You've earned 99 new loyalty points and have 250 points remaining after this order.
```

---

## 7. Test 6 — Browser Tool (Terminal Output)

**Command:**
```bash
agentcore invoke '{"prompt": "Go to https://www.amazon.com and tell me the page title.", "customer_id": "CUST-123", "session_id": "t6"}'
```

**Terminal Output:**
```text
┌────────────────────────── customer_support_agent ───────────────────────────┐
│ Session: d420e0ad-810e-4a8b-9ea9-ebd30a30e640                               │
│ Request ID: 0bd7c630-13e5-481a-a6bf-edb06f05cddb                            │
│ ARN:                                                                        │
│ arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_a │
│ gent-mg3iJ3AQ0b                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Response:
I apologize for the inconvenience. It seems there was an issue initializing the browser session due to authorization restrictions with the automation service. Unfortunately, I'm unable to directly access external websites like Amazon.com at the moment due to these technical limitations.

However, I can still help you with other aspects of your account, such as checking your order status, processing returns, or calculating loyalty discounts.
```

---

## 8. Written Reflection (270 Words)

### Architecture Decisions & Technical Trade-offs
Designing a production AI customer support agent on Amazon Bedrock AgentCore required balancing modularity, security, and response latency. By leveraging the Model Context Protocol (MCP) through the AgentCore Gateway, backend services (API Gateway and AWS Lambda) were decoupled from model orchestration. This architecture eliminates monolithic prompt bloat and grants the model dynamically discovered, strongly-typed tool schemas. For numeric loyalty computations, delegating arithmetic to the sandboxed AgentCore Code Interpreter eliminated LLM hallucination risks on financial totals.

### Challenges Encountered and Resolutions
During deployment, two primary challenges were resolved:
1. **MCP OpenAPI Target Compatibility**: The AgentCore Gateway requires explicit method responses (`200 OK`) and method/path tool overrides when importing REST API Gateways that lack pre-existing `operationId` definitions. Programmatically configuring these mappings resolved gateway target synchronization.
2. **Cross-Session Memory Authorization**: The agent runtime's auto-generated execution role initially restricted access to an ephemeral STM memory resource. Updating the IAM role policy to permit data plane actions (`bedrock-agentcore:CreateEvent`, `RetrieveMemoryRecords`) on the custom LTM resource enabled seamless persistent recall across disparate session IDs.

### Production Scaling & Enterprise Security
For enterprise production deployments, several security and scaling enhancements are recommended:
- **Workload Identity & OAuth 2.0**: Transition from IAM role-level gateway access to fine-grained OAuth 2.0 customer tokens via AgentCore Identity, ensuring tool calls are scoped to authenticated end-user permissions.
- **Bedrock Guardrails**: Integrate PII masking (redacting credit card numbers and addresses) and toxic content filters at the model invocation layer.
- **Autonomous Cache Layering & Rate Limiting**: Deploy Redis caching for frequent knowledge base queries and implement token bucket throttling on the API Gateway to prevent downstream resource exhaustion.
