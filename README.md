# AI Defense Lab for Payment Security

**Mastercard Innovation Challenge · Global Fintech Fest 2026**

A closed-loop red-team/blue-team AI system for payment fraud: it **identifies**
novel GenAI-powered fraud vectors, **generates** high-fidelity simulated attacks
at scale, and **defends** against them with a trained detection model — feeding
detection gaps back into attack generation to continuously harden itself.

## Architecture

```
IDENTIFY  ──▶  GENERATE  ──▶  DEFEND
   ▲                             │
   └─────── feedback loop ───────┘
     (missed attacks → harder variants → retrain)
```

## Repository structure

```
identify/attack_taxonomy.md      Research: all 8 attack vectors, all 8 simulated
generate/base_transactions.py    Synthetic legitimate transaction generator
generate/generators/             One module per attack family (8 total)
generate/run_generation.py       Orchestrates full labeled dataset creation
defend/features.py               Feature engineering (velocity, deviation, auth, device, dispute, etc.)
defend/train.py                  XGBoost classifier training
defend/evaluate.py               Precision/recall/F1/AUC + per-attack breakdown
loop/feedback_loop.py            Closed-loop: finds misses, hardens, retrains
webapp/index.html                Working prototype (open directly in a browser)
data/                            Generated datasets and evaluation results
```

## Attacks simulated (8 / 8)

1. **Behavioral Mimicry Fraud** — AI agent blends fraud into a learned spending profile
2. **AI-Paced Card Testing** — human-timed probing sequences that evade rate limits
3. **Synthetic Identity ("Bust-Out") Fraud** — GenAI identity builds trust, then cashes out
4. **Transaction Laundering** — fake GenAI storefronts disguise illicit high-value transactions
5. **Deepfake Voice ATO** — voice clone talks a call-center agent into an OTP override
6. **Personalized Phishing ATO** — stolen credentials used from a brand-new device, probe then payout
7. **Chargeback Narrative Fraud** — GenAI-templated dispute narratives filed against normal-looking purchases
8. **Biometric Spoofing** — synthetic face/voice defeats a high-value transaction's step-up challenge

Attacks 5–8 were previously documented-only (they naturally live in
audio/text/image data). They're now represented as structured, model-ready
proxy features — authorization channel, device familiarity, auth/match
confidence, dispute + narrative-similarity signals — on the same transaction
schema, so the same tabular pipeline can generate, detect, and harden against
all 8. See `identify/attack_taxonomy.md` for the full reasoning.

## Results (from the included run)

| Metric | Score |
|---|---|
| Precision | 99.83% |
| Recall | 99.91% |
| F1 | 99.87% |
| AUC | 0.99999+ |
| False Positive Rate | 0.01% |

Detection rate by attack type (post feedback-loop): Synthetic Identity,
Card Testing, Transaction Laundering, Deepfake Voice ATO, Biometric Spoofing,
Phishing ATO, and Chargeback Narrative Fraud all 100%; Behavioral Mimicry
98.9% (intentionally the subtlest attack — the one that blends closest to
genuine behavior).

The feedback loop improved F1 from 99.49% (baseline) to 99.87% after two
iterations by regenerating harder variants of the specific attacks that slipped
through.

> **Note on reproducing exact numbers:** the included `data/*.json` results
> were produced with a gradient-boosted tree model in this sandbox (xgboost
> wasn't installable in the offline environment used to extend this project).
> `defend/train.py` still targets XGBoost as originally designed — running
> the pipeline yourself per `requirements.txt` will regenerate `defend/model.pkl`
> and refresh these result files with real XGBoost numbers, which should be
> very close to what's shown here given the same feature set.

## Running it yourself

Requires Python 3.10+.

```bash
pip install -r requirements.txt

# 1. Generate the labeled synthetic dataset (all 8 attacks)
python3 generate/run_generation.py

# 2. Train the detector
python3 defend/train.py

# 3. Evaluate it
python3 defend/evaluate.py

# 4. Run the closed feedback loop (finds misses, hardens attacks, retrains)
python3 loop/feedback_loop.py
```

## Viewing the prototype

No install needed — open `webapp/index.html` directly in any browser. It's a
self-contained page (no server required) that visualizes the closed loop,
lets you run sample transactions from each of the 8 attack families through
the actual trained model's decision logic, and shows the feedback-loop
improvement over iterations.

## Evaluation criteria addressed

- **Diversity of attacks identified**: 8 / 8 vectors researched *and* simulated in depth, each stressing a distinct detection signal
- **Fidelity of attacks in simulation**: per-user behavioral profiles, log-normal spend distributions, realistic timing/geo/device/channel patterns, with deliberate overlap between legit and fraud signals (e.g. some legit disputes and call-center orders exist too) so no single feature is a trivial giveaway
- **Detection algorithms and efficacy**: gradient-boosted classifier (XGBoost in production), full precision/recall/F1/AUC + per-attack-type breakdown
- **Novelty**: the closed feedback loop — missed attacks automatically become harder training data
- **Real-world feasibility**: all eight simulated attacks map to documented, real fraud patterns; detection features are standard payment-industry signals (velocity, deviation, account age, auth confidence, device fingerprinting, dispute-text similarity)
