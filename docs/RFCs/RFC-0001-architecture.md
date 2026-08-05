RFC-0001 — Xyberos Architecture

Title: Core Architecture

Status: Accepted

Summary

Defines the three foundational layers of Xyberos:

Kernel
Runtime
Brain

These layers are mandatory and form the minimum implementation of the platform.

Motivation

The framework should separate platform concerns from cognitive execution.

Instead of placing all logic inside a single Agent class, Xyberos separates responsibilities into independent subsystems.

Architecture
User
 │
 ▼
Runtime
 │
 ▼
Brain
 │
 ▼
LLM

Kernel exists beneath every layer and provides shared services.

Responsibilities
Layer	Responsibility
Kernel	Platform services
Runtime	Cognitive execution
Brain	Reasoning and inference
Non-goals

This RFC does not define the extension subsystems:

Memory
Knowledge
Tools
Planning
Agents
Plugins
Workflows
Events

Those are specified by later RFCs and are implemented in the current codebase.