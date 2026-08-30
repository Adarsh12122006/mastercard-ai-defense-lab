# Attack Taxonomy — GenAI-Powered Payment Fraud

This document catalogs the emerging fraud attack vectors researched for this
challenge. **All 8 are now implemented** in the `generate/` and `defend/`
pillars of this project — the original 4 tabular/pattern-based attacks, plus
4 additional attacks (5–8) that were previously documented-only because they
naturally live in audio/text/image data. Those four are now represented as
**structured, model-ready proxy features** on the same transaction schema
(authorization channel, device familiarity, verification/auth confidence,
dispute + narrative-similarity signals) rather than literal audio/text/image
generation — this keeps every attack usable by the same tabular XGBoost
pipeline while still exercising a genuinely different detection signal per
attack.

## Research landscape (breadth)

| # | Attack Family | How GenAI changes it | Simulated? | Detection signal(s) stressed |
|---|---|---|---|---|
| 1 | **Behavioral Mimicry Fraud** | An AI agent learns a real cardholder's spending profile (merchant categories, amounts, timing, location) from leaked/observed data, then injects fraudulent transactions designed to blend into that profile, evading anomaly-based rules. | ✅ Yes | Amount/time deviation from personal history |
| 2 | **Card Testing / BIN Attack (AI-paced)** | Instead of rapid-fire brute-forcing (easily rate-limited), an LLM-driven agent paces micro-authorizations to mimic human timing variance, spreads attempts across merchants, and adapts retry strategy based on decline codes. | ✅ Yes | Transaction velocity + category scatter |
| 3 | **Synthetic Identity Onboarding** | GenAI generates fully coherent synthetic identities (name, address, SSN-pattern, credit history narrative) that pass KYC checks, then builds a normal-looking transaction history before "busting out" with high-value fraud. | ✅ Yes | Account age + history-thinness mismatch |
| 4 | **Transaction Laundering via Fake Merchants** | LLMs auto-generate convincing fake e-commerce storefronts and product descriptions to disguise illicit transactions (e.g. laundering stolen card funds through a "legitimate-looking" merchant category). | ✅ Yes | Amount vs. category-typical ceiling |
| 5 | **AI Voice/Deepfake Social Engineering (ATO)** | Deepfake voice clones impersonate a cardholder to a call center (or the bank to a cardholder) to authorize fraudulent transactions or extract OTPs. | ✅ Yes | Call-center channel + borderline voice-match confidence + OTP override |
| 6 | **Personalized Phishing at Scale** | LLMs generate thousands of uniquely worded, context-aware phishing messages (referencing real recent purchases scraped from data breaches) to harvest credentials, at a cost and scale impossible manually. | ✅ Yes | Brand-new device + probe-then-payout purchase pattern |
| 7 | **Refund/Chargeback Narrative Fraud** | GenAI produces plausible, varied dispute narratives to file fraudulent chargebacks at scale while evading text-similarity fraud filters. | ✅ Yes | Dispute filed + high similarity to known fraud-narrative template clusters |
| 8 | **Biometric Spoofing for Step-Up Auth** | Synthetic face/voice used to defeat biometric step-up authentication during high-value transaction verification. | ✅ Yes | App-biometric channel + borderline match confidence on a high-value transaction |

## Why structured proxies instead of literal audio/text/image generation

Real payment fraud detection operates primarily on transaction-level and
authorization-level metadata — not the raw audio of a phone call or the raw
text of a phishing email. What actually reaches a detection model in
production is metadata about *how* a transaction was authorized: which
channel, what confidence score the verification system produced, whether a
step-up challenge was bypassed, whether a dispute was filed and how it scores
against known fraud-narrative clusters. Modeling attacks 5–8 as those
metadata signals is how a real fraud team would represent them in a tabular
detection pipeline — it's a faithful representation of the *consequence* of
the GenAI attack on the payments system, without requiring this prototype to
run actual voice-cloning, phishing-text-generation, or face-swap models
(which would be a distraction from — and out of scope for — building a
working closed-loop detection pipeline, and would raise obvious misuse
concerns for a public hackathon repo).

## Why these signals, specifically, for attacks 5–8

- **Deepfake Voice ATO** → the deepfake doesn't change the transaction
  itself; it changes the *authorization event*. It routes through the
  call-center channel, the agent verification confidence is measurably
  lower than a genuine live match, and it typically talks the agent into
  an OTP override ("I can't access my phone, I'm traveling").
- **Personalized Phishing ATO** → credentials are correct (so login itself
  doesn't fail), but the session runs from a device this user has never
  used before, and shows the classic probe-then-payout pattern: a small
  purchase to confirm the stolen credentials still work, followed shortly
  by a larger one.
- **Chargeback Narrative Fraud** → the *purchase* looks completely normal
  (the point of this attack is that the fraud lives entirely in what
  happens afterward). The signal is in the dispute: filed unusually fast,
  and scoring high similarity against known GenAI-template narrative
  clusters — vs. genuine disputes, which are rarer, slower, and don't
  cluster tightly.
- **Biometric Spoofing** → triggers specifically on transactions large
  enough to invoke the app's biometric step-up challenge, through the
  app-biometric channel, with a match confidence that cleared the pass
  threshold but sits well below a genuine match.

Each of the 8 attacks now stresses a **distinct** detection signal, so the
classifier has to learn 8 genuinely different failure modes rather than
variations on one theme — directly addressing the "diversity" judging
criterion at full documented breadth, not just the 4-attack subset.

## Real-world feasibility

All eight attacks are grounded in patterns documented in industry fraud
reports. The GenAI-driven element in each case is the **evasion
sophistication** — smarter pacing, better blending, more convincing
synthetic voice/identity/narrative — not the fraud mechanism itself, which
matches how real fraud rings are actually adopting these tools.
