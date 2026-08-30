# Attack Taxonomy — GenAI-Powered Payment Fraud

This document catalogs the emerging fraud attack vectors researched for this
challenge, and identifies which ones are implemented in the `generate/` and
`defend/` pillars of this project.

## Research landscape (breadth)

| # | Attack Family | How GenAI changes it | Simulated? |
|---|---|---|---|
| 1 | **Behavioral Mimicry Fraud** | An AI agent learns a real cardholder's spending profile (merchant categories, amounts, timing, location) from leaked/observed data, then injects fraudulent transactions designed to blend into that profile, evading anomaly-based rules. | ✅ Yes |
| 2 | **Card Testing / BIN Attack (AI-paced)** | Instead of rapid-fire brute-forcing (easily rate-limited), an LLM-driven agent paces micro-authorizations to mimic human timing variance, spreads attempts across merchants, and adapts retry strategy based on decline codes. | ✅ Yes |
| 3 | **Synthetic Identity Onboarding** | GenAI generates fully coherent synthetic identities (name, address, SSN-pattern, credit history narrative) that pass KYC checks, then builds a normal-looking transaction history before "busting out" with high-value fraud. | ✅ Yes |
| 4 | **Transaction Laundering via Fake Merchants** | LLMs auto-generate convincing fake e-commerce storefronts and product descriptions to disguise illicit transactions (e.g. laundering stolen card funds through a "legitimate-looking" merchant category). | ✅ Yes |
| 5 | **AI Voice/Deepfake Social Engineering (ATO)** | Deepfake voice clones impersonate a cardholder to a call center or impersonate a bank to a cardholder (vishing) to authorize fraudulent transactions or extract OTPs. | ⚪ Documented only (not simulated — requires audio, out of scope for transaction-level data) |
| 6 | **Personalized Phishing at Scale** | LLMs generate thousands of uniquely worded, context-aware phishing messages (referencing real recent purchases scraped from data breaches) to harvest credentials, at a cost and scale impossible manually. | ⚪ Documented only |
| 7 | **Refund/Chargeback Narrative Fraud** | GenAI produces plausible, varied dispute narratives to file fraudulent chargebacks at scale while evading text-similarity fraud filters. | ⚪ Documented only |
| 8 | **Biometric Spoofing for Step-Up Auth** | Synthetic face/voice used to defeat biometric step-up authentication during high-value transaction verification. | ⚪ Documented only |

We prioritized **depth on 4 tractable, data-representable attacks** (rows 1–4)
that can be faithfully simulated as transaction-level data, over shallow
coverage of all 8. Rows 5–8 are documented for breadth but require
non-tabular modalities (audio, text, images) outside this prototype's scope;
they are noted as future extensions in the solution walkthrough.

## Why these four

Real payment fraud detection operates primarily on transaction-level
features (amount, merchant category, timing, location, velocity). The four
selected attacks each stress a **different detection signal**, which gives
the classifier genuine diversity to learn from rather than four variations
of the same pattern:

- **Behavioral Mimicry** → stresses profile-deviation features
- **Card Testing** → stresses velocity / timing features
- **Synthetic Identity** → stresses account-age / history-consistency features
- **Transaction Laundering** → stresses merchant-category / amount-distribution features

## Real-world feasibility

All four attacks are grounded in patterns documented in industry fraud
reports (card testing and synthetic identity fraud are both named as
top-growing categories by payment networks). The GenAI-driven element in
each case is the **evasion sophistication** — smarter pacing, better
blending, more convincing synthetic data — not the fraud mechanism itself,
which matches how real fraud rings are actually adopting these tools.
