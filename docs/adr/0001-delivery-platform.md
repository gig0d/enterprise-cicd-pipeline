# ADR 0001: GitHub Actions, Docker, Python, and ephemeral staging

- Status: accepted for the portfolio MVP
- Date: 2026-10-27

## Context

Demonstrate real CI/CD and DevSecOps operations, remain maintainable by an individual university student, support Windows development, and avoid paid hosting or an oversized application.

## Decision

Use GitHub Actions to keep source, PR checks, permissions, artifacts, environments, and release controls on one auditable platform. GitHub-hosted Ubuntu runners provide disposable Linux container verification. Publication is limited to trusted `main` jobs with scoped package permission.

Use Docker to create an immutable registry candidate promoted by digest. Generate BuildKit provenance and an SPDX SBOM, pin the official base image by digest, hash production dependencies, and run without root privileges.

Use Python 3.13, FastAPI, Pydantic, Uvicorn, and a small in-memory inventory. The example demonstrates validation, readiness, HTTP behavior, and graceful shutdown without database administration. Portable Python commands work on Windows and Ubuntu without requiring Make.

Use ephemeral runner containers for staging and production/recovery simulation. This enables actual startup, HTTP, failure, and cleanup checks without cloud credentials or a public endpoint. GitHub Environments provide configurable policy boundaries, not hosting.

## Consequences

The delivery path is inspectable without a cloud subscription. Docker and network access remain required for relevant checks. There is no durable inventory, persistent staging URL, production traffic switching, or storage rollback. Reviewer enforcement and branch protections require separate owner-controlled setup. Persistent infrastructure and independent signature enforcement remain future decisions requiring a demonstrated need and owner approval.
