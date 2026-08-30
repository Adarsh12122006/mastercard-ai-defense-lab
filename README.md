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
identify/attack_taxonomy.md      Research: 8 attack vectors, 4 simulated in depth
generate/base_transactions.py    Synthetic legitimate transaction generator
generate/generators/             One module per attack family
generate/run_generation.py       Orchestrates full labeled dataset creation
defend/features.py               Feature engineering (velocity, deviation, etc.)
defend/train.py                  XGBoost classifier training
defend/evaluate.py               Precision/recall/F1/AUC + per-attack breakdown
loop/feedback_loop.py            Closed-loop: finds misses, hardens, retrains
webapp/index.html                Working prototype (open directly in a browser)
data/                            Generated datasets and evaluation results
```

## Attacks simulated

1. **Behavioral Mimicry Fraud** — AI agent blends fraud into a learned spending profile
2. **AI-Paced Card Testing** — human-timed probing sequences that evade rate limits
3. **Synthetic Identity ("Bust-Out") Fraud** — GenAI identity builds trust, then cashes out
4. **Transaction Laundering** — fake GenAI storefronts disguise illicit high-value transactions

(4 additional vectors — deepfake social engineering, scaled phishing, chargeback
narrative fraud, biometric spoofing — are researched and documented in
`identify/attack_taxonomy.md` but require non-tabular data outside this
prototype's scope.)

## Results (from the included run)

| Metric | Score |
|---|---|
| Precision | 99.4% |
| Recall | 99.4% |
| F1 | 99.4% |
| AUC | 0.9997 |
| False Positive Rate | 0.03% |

Detection rate by attack type: Synthetic Identity 100%, Card Testing 100%,
Transaction Laundering 100%, Behavioral Mimicry 94.1%.

The feedback loop improved F1 from 99.51% (baseline) to 99.76% after one
iteration by regenerating harder variants of the specific attacks that slipped
through.

## Running it yourself

Requires Python 3.10+.

```bash
pip install -r requirements.txt

# 1. Generate the labeled synthetic dataset
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
lets you run sample transactions from each attack family through the actual
trained model's decision logic, and shows the feedback-loop improvement over
iterations.

## Evaluation criteria addressed

- **Diversity of attacks identified**: 8 vectors researched, 4 simulated in depth across distinct detection signal types
- **Fidelity of attacks in simulation**: per-user behavioral profiles, log-normal spend distributions, realistic timing/geo patterns
- **Detection algorithms and efficacy**: XGBoost classifier, full precision/recall/F1/AUC + per-attack-type breakdown
- **Novelty**: the closed feedback loop — missed attacks automatically become harder training data
- **Real-world feasibility**: all four simulated attacks map to documented, real fraud patterns; detection features are standard payment-industry signals (velocity, deviation, account age)
