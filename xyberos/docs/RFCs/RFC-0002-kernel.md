RFC-0002 — Kernel

Defines the Kernel subsystem.

Purpose

The Kernel owns shared platform services.

It is responsible for:

configuration
logging
dependency registration
lifecycle
future event system

It never performs reasoning.

Initial Services
Kernel
├── Config
└── Logger

Future revisions may add:

Kernel
├── Config
├── Logger
├── EventBus
├── Storage
├── PluginManager
├── Scheduler
└── Security