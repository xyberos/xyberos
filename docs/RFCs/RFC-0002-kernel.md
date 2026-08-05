RFC-0002 — Kernel

Defines the Kernel subsystem.

Purpose

The Kernel owns shared platform services.

It is responsible for:

configuration
logging
dependency registration
lifecycle
event bus
plugin management

It never performs reasoning.

Current Services
Kernel
├── Config
├── Logger
├── Registry
├── EventBus
└── PluginManager

Future revisions may add:

Kernel
├── Storage
├── Scheduler
└── Security