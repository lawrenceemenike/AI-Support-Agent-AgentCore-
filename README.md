# AI-Support-Agent-AgentCore

# 🛒 Production AI Customer Support Agent with Amazon Bedrock AgentCore & Strands SDK

[![AWS Bedrock](https://img.shields.io/badge/AWS-Amazon%20Bedrock%20AgentCore-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/bedrock/)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Strands SDK](https://img.shields.io/badge/Framework-Strands%20SDK-5A67D8)](https://github.com/)
[![MCP Protocol](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-00B4D8)](https://modelcontextprotocol.io/)

An enterprise-grade, multi-tool AI Customer Support Agent built with **Amazon Bedrock AgentCore** and the **Strands SDK**. The assistant serves as an intelligent customer interface capable of handling order tracking, return processing, grounded product lookups, long-term personalized memory across sessions, deterministic loyalty calculations, and live web access.

---

## 📑 Table of Contents

- [Overview & Key Features](#-overview--key-features)
- [System Architecture](#-system-architecture)
- [Deployed AWS Infrastructure](#-deployed-aws-infrastructure)
- [Repository Structure](#-repository-structure)
- [Setup & Deployment Guide](#-setup--deployment-guide)
- [Verification Test Scenarios & Logs](#-verification-test-scenarios--logs)
- [Technical Architecture & Scaling Reflection](#-technical-architecture--scaling-reflection)

---

## 🌟 Overview & Key Features

- **🔌 Model Context Protocol (MCP) via AgentCore Gateway**: Integrates REST API Gateway endpoints (`order-tracker`) and direct AWS Lambda handlers (`refund-processor`) with dynamic tool discovery.
- **🧠 Cross-Session Long-Term Memory (LTM)**: Employs **AgentCore Memory** with dual extraction strategies (Semantic Fact Extraction and User Preference Extraction) to persist customer context across sessions.
- **📚 Grounded Knowledge Base (RAG)**: Integrates product catalogs, warranty policies, return rules, and tier specifications via Bedrock Knowledge Base and semantic search.
- **🧮 Code Interpreter Sandbox**: Utilizes **AgentCore Code Interpreter** to execute deterministic Python arithmetic for multi-tier discounts, point redemptions, and order totals.
- **🌐 Live Browser Automation**: Integrates **AgentCore Browser** to navigate web pages with structured policy and permission management.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    User([Customer Interaction]) --> AgentRuntime[Amazon Bedrock AgentCore Runtime]
    
    subgraph AgentRuntime [Bedrock AgentCore Container Runtime]
        Agent[Strands SDK Agent: customer_support_agent]
        Model[Amazon Nova-2-Lite / Claude 3.5]
        MemHook[MemoryHook / Context Prepending]
    end

    Agent -->|MCP Protocol| Gateway[AgentCore Gateway]

    subgraph ToolIntegrations [Tool Integrations & Backend Services]
        Gateway -->|REST Proxy| APIGW[API Gateway: CustomerSupportOrderAPI]
        APIGW -->|Lambda Proxy| OrderLambda[Lambda: order-tracker]
        Gateway -->|Direct Invoke| RefundLambda[Lambda: refund-processor]
        
        Agent -->|RAG Retrieval| KB[(Bedrock Knowledge Base / S3)]
        Agent -->|Python Code Sandbox| Sandbox[AgentCore Code Interpreter]
        Agent -->|Web Navigation| Browser[AgentCore Browser Tool]
    end
    
    MemHook <-->|Store & Retrieve Facts/Preferences| Memory[(AgentCore Memory LTM)]
