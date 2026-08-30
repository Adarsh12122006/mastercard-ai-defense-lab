# Attack Taxonomy — GenAI-Powered Payment Fraud

This document catalogs the fraud attack vectors researched for this challenge,
organized into five categories, and identifies which are implemented as
working code in `generate/` and defended against in `defend/`.

**9 of 13 researched vectors are fully simulated and defended in code** —
including two attacks that target the AI system itself rather than being
detected by it (adversarial evasion of the classifier, and prompt injection
against AI-powered fraud-ops tooling), which we consider the most
hackathon-relevant additions given the "AI Defense Lab" framing.

## Category 1 — Identity & Onboarding Attacks

| Attack | GenAI Role | Status |
|---|---|---|
| Deepfake KYC bypass | Synthetic video/audio to pass liveness checks during onboarding or step-up auth | Documented |
| Voice clone account takeover | Cloned voice against call-center authentication | Documented |
| Synthetic document forgery | GenAI-generated IDs/pay stubs/utility bills that pass OCR verification | Documented |
| Deepfake biometric spoofing | Face-swap / 3D-mask attacks against selfie liveness checks | Documented |
| **Synthetic Identity Onboarding** ("bust-out") | Coherent fake identity builds a thin transaction history, then busts out with high-value fraud | **Simulated** |

*Only Synthetic Identity is representable as transaction-level data; the other four require audio/video/image modalities outside this prototype's scope.*

## Category 2 — Social Engineering at Scale

| Attack | GenAI Role | Status |
|---|---|---|
| AI-personalized phishing/smishing | LLM-generated messages tailored per-victim from scraped/leaked data | Documented |
| Chatbot-driven pretexting | AI agent conducts multi-turn "bank support" conversation to extract OTPs/card details | Documented |
| Romance/investment scam bots | Long-horizon LLM personas building trust over weeks before requesting payment | Documented |
| Deepfake CEO/vendor fraud (BEC) | Voice/video deepfakes authorizing wire transfers or vendor payment changes | Documented |

*This entire category requires text/audio/video content generation and multi-turn conversation modeling — a different project scope from transaction-level fraud detection. Documented here for completeness of the threat landscape.*

## Category 3 — Transaction & Behavioral Attacks

| Attack | GenAI Role | Status |
|---|---|---|
| **Behavioral Mimicry Fraud** | AI agent learns a victim's spending profile and injects fraud designed to blend in | **Simulated** |
| **AI-Paced Card Testing** | Human-timed probing sequences that evade rate-limit rules | **Simulated** |
| **Adversarial Evasion of the Deployed Classifier** | Attacker probes our own trained model as a black box, binary-searches for its decision boundary, crafts transactions that hug the "legitimate" side | **Simulated** |
| **Generative-Model-Based Synthetic Fraud** | A generative model (here: Gaussian Mixture as a lightweight stand-in for a full GAN) produces fraud statistically indistinguishable from legitimate transactions | **Simulated** |
| Model inversion / membership inference | Inferring training data (real cardholder behavior) from a deployed model's outputs | Documented |

Adversarial Evasion also serves as our implementation of two related ideas from the brief: **model/API extraction** (the technique — repeatedly querying a scoring endpoint to reconstruct its decision logic — is identical) and an **adaptive attacker** that adjusts its strategy live based on the model's own feedback (our binary-search probing is a simplified, deterministic stand-in for a full reinforcement-learning agent, chosen for reproducibility within the hackathon timeline).

## Category 4 — Merchant & Ecosystem Attacks

| Attack | GenAI Role | Status |
|---|---|---|
| **Transaction Laundering** | GenAI-generated fake storefronts disguise illicit transactions through a plausible merchant category | **Simulated** |
| **Autonomous Storefront Churn** | Fake storefronts (auto-generated listings, reviews, support) spun up, burst-processed, and torn down before merchant-risk monitoring catches on | **Simulated** |
| Refund/chargeback narrative fraud | LLM-generated dispute narratives crafted to match auto-approval triggers | Documented |
| **Loyalty/Rewards Program Abuse** | AI-orchestrated bot network farms signup bonuses / reward points at scale | **Simulated** |

## Category 5 — Infrastructure-Level Attacks

| Attack | GenAI Role | Status |
|---|---|---|
| **Prompt Injection Against AI Fraud-Ops Tooling** | Malicious instructions embedded in transaction memo/text fields, targeting an LLM-based fraud analyst assistant rather than the numerical classifier | **Simulated** |
| Data poisoning of the detection model | Slowly injecting mislabeled transactions via a compromised feedback pipeline to degrade the model over time | Documented |
| Model/API extraction | Repeatedly querying a fraud-scoring API to reconstruct its decision logic for resale as a "fraud-as-a-service" tool | Documented (technique shared with Adversarial Evasion above) |

Prompt Injection is architecturally distinct from every other attack in this
taxonomy: it does not try to fool the numerical fraud model at all. It targets
a *different* AI component (an LLM reading transaction text), so it is
defended by a separate guardrail layer (`defend/prompt_injection_guard.py`),
not by the XGBoost classifier's features.

## Summary: why these 9 were chosen for full simulation

| Attack | Detection signal it stresses |
|---|---|
| Behavioral Mimicry | Amount/timing deviation from personal history |
| Card Testing | Transaction velocity |
| Synthetic Identity | Account age / history-thinness |
| Transaction Laundering | Amount vs. category-typical ceiling |
| Adversarial Evasion | Requires adversarial retraining, not a static feature |
| Generative Synthetic Fraud | Category familiarity (looks normal, but foreign to this user) |
| Storefront Churn | Merchant lifespan / transaction velocity per merchant |
| Loyalty Abuse | New-account geographic clustering |
| Prompt Injection | Text-pattern guardrail (separate defense layer entirely) |

Each of the 9 stresses a **genuinely different** detection mechanism — this
was the deciding factor in scope, over breadth-without-depth across all 13.
The 4 documented-only vectors (deepfake/voice/document/biometric spoofing,
the entire social-engineering category, model inversion, chargeback-narrative
fraud, and data poisoning) require audio, video, image, or free-form
conversational modalities that are a different engineering scope from
transaction-level fraud detection, and are noted here as natural next phases.
