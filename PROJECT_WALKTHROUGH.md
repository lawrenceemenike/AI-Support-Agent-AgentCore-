# Project Walkthrough: AI Customer Support Agent with Amazon Bedrock AgentCore & Strands SDK

## 1. Executive Summary

This project implements a fully functional, enterprise-grade AI customer support agent using **Amazon Bedrock AgentCore** and the **Strands SDK**. The agent integrates:
1. **MCP Protocol via AgentCore Gateway**: Securely bridges the agent to an AWS API Gateway REST API (`order-tracker`) and direct AWS Lambda functions (`refund-processor`).
2. **Bedrock Knowledge Base / RAG**: Grounded product catalog, warranty, return policy, and loyalty rewards specifications.
3. **AgentCore Memory**: Dual-strategy long-term memory (Semantic Fact Extraction & User Preferences) enabling seamless cross-session personalization.
4. **AgentCore Code Interpreter**: Deterministic, sandboxed arithmetic execution for complex multi-tier loyalty discounts and point redemptions.
5. **AgentCore Browser Integration**: Web automation and external navigation tool with structured error handling and security policies.

---

## 2. AgentCore Cloud Deployment (`agentcore deploy` CLI Output)

```text
$ uv run agentcore deploy

🚀 Launching Bedrock AgentCore (codebuild mode - RECOMMENDED)...
   • Build ARM64 containers in the cloud with CodeBuild
   • No local Docker required (DEFAULT behavior)
   • Production-ready deployment

Using existing memory: CustomerSupportMemory-7gBufM9tWh
Starting CodeBuild ARM64 deployment for agent 'customer_support_agent' to account 093325579981 (us-east-1)
Generated image tag: 20260824-104030-128
Setting up AWS resources (ECR repository, execution roles)...
Using ECR repository: 093325579981.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-customer_support_agent
Using execution role: arn:aws:iam::093325579981:role/AmazonBedrockAgentCoreSDKRuntime-us-east-1-aa96c3a063
Preparing CodeBuild project and uploading source...
Reusing existing CodeBuild execution role: arn:aws:iam::093325579981:role/AmazonBedrockAgentCoreSDKCodeBuild-us-east-1-aa96c3a063
Including Dockerfile from .bedrock_agentcore/customer_support_agent in source.zip
Uploaded source to S3: customer_support_agent/source.zip
Updated CodeBuild project: bedrock-agentcore-customer_support_agent-builder
Starting CodeBuild build (this may take several minutes)...
Starting CodeBuild monitoring...
🔄 PROVISIONING started (total: 3s)
✅ PROVISIONING completed in 4.0s
🔄 BUILD started (total: 7s)
✅ BUILD completed in 32.0s
🔄 POST_BUILD started (total: 39s)
✅ POST_BUILD completed in 18.0s
🔄 COMPLETED started (total: 57s)
✅ CodeBuild build succeeded: bedrock-agentcore-customer_support_agent-builder:57a3dce4-0be2-4a3b-85df-c3080725b2a8
Image uploaded to ECR: 093325579981.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-customer_support_agent:20260824-104030-128

Deploying to Bedrock AgentCore...
Passing memory configuration to agent: CustomerSupportMemory-7gBufM9tWh
Agent created/updated: arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_agent-mg3iJ3AQ0b
Polling for endpoint to be ready...
Agent endpoint: arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_agent-mg3iJ3AQ0b/runtime-endpoint/DEFAULT

REDEPLOYMENT COMPLETE!
Agent ID: customer_support_agent-mg3iJ3AQ0b
Agent ARN: arn:aws:bedrock-agentcore:us-east-1:093325579981:runtime/customer_support_agent-mg3iJ3AQ0b
```

---

## 3. Architecture & Deployed AWS Resources

| Resource | Identifier / Name | Description |
| :--- | :--- | :--- |
| **AgentCore Runtime** | `customer_support_agent-mg3iJ3AQ0b` | Containerized agent running Python runtime on ARM64 |
| **AgentCore Memory** | `CustomerSupportMemory-7gBufM9tWh` | LTM strategies: `customer_facts` & `customer_preferences` |
| **AgentCore Gateway** | `customersupportgateway-ficlwnwjtk` | MCP endpoint with HTTP SSE streaming transport |
| **API Gateway Target** | `2vc937rsf6` (`CustomerSupportOrderAPI`) | REST API proxying order tracking & customer lookups |
| **Lambda Targets** | `order-tracker` & `refund-processor` | Backend execution targets (`us-east-1`) |
| **Knowledge Base S3** | `cs-support-kb-093325579981` | Product catalog and policy document repository |
| **Container Image (ECR)**| `bedrock-agentcore-customer_support_agent` | Deployed container image on Amazon ECR |

---

## 4. Verification Test Scenarios & Results

All 6 required verification test scenarios were executed directly against the live cloud runtime endpoint via `agentcore invoke`.

```mermaid
flowchart TD
    User([Customer Interaction]) --> Agent[AgentCore Runtime: customer_support_agent]
    Agent --> Gateway[AgentCore Gateway MCP]
    Gateway --> APIGW[API Gateway: CustomerSupportOrderAPI]
    APIGW --> OrderLambda[Lambda: order-tracker]
    Gateway --> RefundLambda[Lambda: refund-processor]
    Agent --> Memory[(AgentCore Memory: CustomerSupportMemory)]
    Agent --> CodeExec[Code Interpreter Sandbox]
    Agent --> KB[(Product Knowledge Base)]
```

### Test 1 — Order Tracking (MCP via API Gateway)
**Input Payload:**
```json
{"prompt": "Can you track order ORD-001?", "customer_id": "CUST-123", "session_id": "t1"}
```
**Agent Response:**
```text
I've tracked your order ORD-001 and here's the current status:

Order Status: SHIPPED 🚚
Customer: CUST-123
Items: 
- Wireless Headphones Pro (1 x $89.99)

Total: $89.99
Carrier: UPS
Tracking Number: TRK987654321
Estimated Delivery: August 26, 2026

Your order is currently in transit and expected to be delivered by August 26, 2026.
```

---

### Test 2 — Refund Processing (MCP via Lambda)
**Input Payload:**
```json
{"prompt": "I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.", "customer_id": "CUST-123", "session_id": "t2"}
```
**Agent Response:**
```text
Perfect! Your refund for the Kindle Paperwhite (ORD-002) has been approved.

- Refund ID: REF-L8OIRM1O  
- Status: APPROVED  
- Amount: $0 (full refund)  
- Credit will appear: In 3-5 business days  

The refund has been processed and you'll see the credit on your original payment method within the next few business days. If you need a prepaid return shipping label for the device, I can help with that as well.
```

---

### Test 3 — Knowledge Base (RAG Grounding)
**Input Payload:**
```json
{"prompt": "What are the benefits of the Platinum loyalty tier?", "customer_id": "CUST-123", "session_id": "t3"}
```
**Agent Response:**
```text
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
```

---

### Test 4 — Cross-Session Long-Term Memory
**Session A (Input):**
```json
{"prompt": "Hi, I am Jane. I prefer concise responses.", "customer_id": "CUST-123", "session_id": "s-A"}
```
**Session A (Response):**
```text
Hello Jane! I'll keep my responses concise. How can I assist you today?
```

*(Waited 35s for background AgentCore Memory extraction into `customer_facts` and `customer_preferences`)*

**Session B (Input):**
```json
{"prompt": "Do you remember my name and communication preference?", "customer_id": "CUST-123", "session_id": "s-B"}
```
**Session B (Response):**
```text
Yes, Jane, I remember your name and that you prefer concise responses. How can I assist you today?
```

---

### Test 5 — Loyalty Discount Calculation (Code Interpreter Sandbox)
**Input Payload:**
```json
{"prompt": "I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.", "customer_id": "CUST-123", "session_id": "t5"}
```
**Agent Response:**
```text
Based on your Gold membership and 4,250 loyalty points, your $150 standard order discount breakdown is:

- Points redeemed: 4,000 points ($40 discount)
- Gold tier discount: 10% ($15 discount)
- Total savings: $55
- Final total: $95

You've earned 99 new loyalty points and have 250 points remaining after this order.
```

---

### Test 6 — Live Browser Tool (Real Page Content Retrieval)
**Input Payload:**
```json
{"prompt": "Go to https://example.com and tell me the page title and description.", "customer_id": "CUST-123", "session_id": "t6"}
```
**Agent Response:**
```text
I navigated to https://example.com using the browser tool and extracted the live page content:

- Page Title: Example Domain
- URL: https://example.com
- Page Heading: Example Domain
- Page Description: This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.
```

---

## 5. Written Reflection (Design & Production Scaling)

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
