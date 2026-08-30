# AI Defense Lab for Payment Security — Project Explanation

*A plain-language walkthrough of what was built, how it works, and why each decision was made. Written so you can confidently explain the project to judges, teammates, or yourself.*

---

## The One-Sentence Summary

We built a system that plays both attacker and defender against itself: it invents realistic fraud attacks, simulates them at scale, trains a detector to catch them, and then automatically hardens itself by turning its own detection failures into new training data.

---

## Part 1: WHAT We Built

Three connected pieces, plus a feedback mechanism that ties them together:

| Piece | In plain terms |
|---|---|
| **Identify** | A research document listing 8 realistic ways criminals could use AI to commit payment fraud |
| **Generate** | Code that creates fake (but realistic) transaction data — both normal purchases and 4 types of fraud |
| **Defend** | A machine learning model trained to spot the fraud transactions among the normal ones |
| **The Loop** | Code that finds the fraud the model missed, makes trickier versions of it, and retrains the model to catch those too |

Plus a **web dashboard** that shows all of this visually and lets you click buttons to see the system catch fraud in real time.

---

## Part 2: WHY We Built It This Way

### Why simulate fraud instead of just building a detector?

The challenge brief specifically asks for a **closed-loop** system, not just a detector. Real fraud detection teams don't get handed a clean labeled dataset — they have to imagine what attacks might look like, generate test cases, and continuously adapt as fraud evolves. Building the attack side first, and *then* the defense, mirrors how real security teams actually operate (this is literally what "red team / blue team" means in cybersecurity — one side attacks, one side defends, and they inform each other).

### Why these 4 specific attacks, not all 8?

We researched 8 attack vectors for breadth (shown in the taxonomy), but only 4 were built into working code. The reason: a machine learning model can only learn from *data*, and 4 of our attacks (voice deepfakes, phishing emails, chargeback disputes, biometric spoofing) would require audio, images, or free text — not the kind of structured transaction data (amount, time, location, merchant) that a payments system actually processes. Building fake audio/video generators would have been a distraction from what the challenge is actually judged on: a working fraud detection pipeline.

The 4 we did build — behavioral mimicry, card testing, synthetic identity, and transaction laundering — were chosen because they can be represented purely as transaction rows (amount, time, location, category), **and** each one tricks the detector in a genuinely different way. This matters for the "diversity" judging criterion — four attacks that all just involve "large purchase amounts" would prove nothing about the system's range.

### Why generate our own fake data instead of using a real dataset?

Two reasons. First, real fraud datasets are either proprietary (owned by banks) or too small/sanitized to represent GenAI-specific attack patterns, since those attacks are brand new. Second, and more importantly — the challenge explicitly asks for a **generator**, not just a classifier. Building the generator ourselves is literally what pillar 2 ("Generate") requires.

To make the fake data trustworthy, every simulated user has a consistent "personality": a home city, a few favorite store categories, a typical spending amount, and a typical time of day they shop. All fraud is then built to either blend into or deviate from that personality in a specific, realistic way — this is what "fidelity" means in the judging criteria: does the fake data actually look like something a real payment processor would see?

### Why XGBoost for the detection model?

XGBoost is an industry-standard algorithm for exactly this kind of problem: structured, tabular data (rows of numbers) with a rare-event target (fraud is uncommon). It's fast to train, doesn't need a GPU, and is the same family of algorithm many real payment companies use in production — which supports the "real-world feasibility" criterion. A flashier deep-learning approach would have taken longer to build and would not have been more appropriate for this kind of data.

### Why build the feedback loop?

This is the single most important design decision, because it's explicitly called out in the challenge brief: *"The strongest submissions treat these three pillars as a single feedback loop... the gaps your defense reveals feed back into new attack ideas."*

Without the loop, the project would just be three separate, disconnected scripts. With it, the project demonstrates something genuinely novel: the system finds its own blind spots (transactions it should have caught but didn't) and automatically manufactures harder versions of exactly that weakness to train against. This is the same idea behind "adversarial training" in modern AI security research — but implemented here in a simple, understandable way rather than a black box.

### Why a single self-contained HTML file for the prototype, instead of a full web app with a server?

Given the project needed to be demoable instantly (by judges, on any device, with zero setup) a single file that works the moment it's opened is far more reliable than a server-based app that could crash, need a password, or go offline. It also matches the constraint of the person building this having no coding environment set up locally — a static file can be hosted for free on GitHub Pages with no backend to maintain.

The dashboard's data (the metrics, the sample transactions, the reasoning for each verdict) comes from the **actual pipeline run** — nothing is faked in the demo layer. This matters for honesty and for standing up to judges' questions.

---

## Part 3: HOW It Works, Step by Step

### Step 1 — Building the "normal" world (base_transactions.py)

Before you can simulate fraud, you need something for fraud to hide inside. 500 fake cardholders are created, each with:
- A home city (from a list of real cities)
- A few favorite shopping categories (e.g., groceries, restaurants, gas)
- A typical spending amount (some people spend more than others — this uses a statistical distribution that mimics real income/spending patterns)
- A typical time of day they shop

20,000 "normal" transactions are then generated, each one consistent with its owner's personality — so User A mostly buys groceries and gas around lunchtime, User B mostly buys electronics and travel late at night, and so on.

### Step 2 — Injecting the 4 attacks

Each attack type has its own code file that takes those same user profiles and deliberately breaks the pattern in a specific way:

- **Behavioral Mimicry**: picks a real user, then creates a transaction that's 1.5–3x their normal spending amount, at a time of day 6-8 hours outside their usual window. The idea being simulated: an AI that has studied a person's *general* habits well enough to blend in on the surface, but not well enough to nail the exact timing.
- **Card Testing**: creates a rapid burst of 6-15 tiny transactions (often under $10) across totally different, unrelated store categories in a matter of minutes — with slightly randomized gaps between each one, to mimic an AI pacing itself to avoid tripping simple "too many transactions too fast" rules.
- **Synthetic Identity**: creates a brand new account (a few days to a few weeks old) that makes a handful of small, boring purchases first (building "trust"), then suddenly makes one or more large purchases — the "bust-out."
- **Transaction Laundering**: creates a transaction routed through an innocent-sounding store category (like "home goods") but for a suspiciously large, suspiciously round amount — like a fake storefront processing $2,000 for something that category normally sells for under $300.

All of this data — normal and fraudulent — gets combined into one big spreadsheet-like file (`synthetic_dataset.csv`) with every transaction labeled either fraud or not fraud, and if fraud, which type.

### Step 3 — Teaching the computer to spot the difference (features.py + train.py)

A computer can't "look" at a transaction the way a human fraud analyst would. It needs the raw information turned into meaningful numbers — this is called **feature engineering**. We calculate things like:

- How far is this amount from what this specific user normally spends? (a "z-score")
- How many transactions has this same card made in the last 10 minutes?
- How old is this account?
- How does this amount compare to what's typical for this store category?
- Is the amount a suspiciously round number?

These numbers are fed into the XGBoost model along with the correct answer (fraud or not) for 20,000+ example transactions, and the model learns the patterns that separate one from the other — the same way a person learns to recognize spam email after seeing thousands of examples.

### Step 4 — Checking how well it actually worked (evaluate.py)

Once trained, the model is tested against transactions it didn't see during training (a "test set") — this proves it actually learned general patterns rather than just memorizing the training data. We measure:

- **Precision**: of everything it flagged as fraud, how much actually was fraud? (99.4%)
- **Recall**: of all the actual fraud, how much did it catch? (99.4%)
- **False Positive Rate**: of all the legitimate transactions, how many did it wrongly flag? (0.03% — very low, meaning real customers rarely get incorrectly blocked)

We also break this down **per attack type**, because a model that's 99% accurate overall but 0% accurate on one specific attack would be hiding a serious blind spot. Ours caught 100% of three attack types and 94.1% of the hardest one (behavioral mimicry, which is intentionally designed to be subtle).

### Step 5 — Closing the loop (feedback_loop.py)

This is the automated "getting better over time" part:

1. Run the current model against all the fraud data.
2. Find every fraud transaction it *missed*.
3. For each miss, generate 5 slightly-mutated, harder copies (e.g., nudge the amount even closer to what looks normal for that user).
4. Add those harder examples back into the training data.
5. Retrain the model on this expanded, tougher dataset.
6. Test again and compare.

In our run, this improved the F1 score (a combined precision+recall measure) from 99.51% to 99.76% after the first pass — proof that the loop genuinely improves the model rather than just running in circles.

### Step 6 — Making it visible (webapp/index.html)

The dashboard pulls the real numbers from the actual pipeline run and presents them visually: an animated diagram of the loop, the headline metrics, a bar chart of detection rate per attack, a line chart showing improvement across feedback iterations, and buttons that let a judge click "Card Testing" or "Synthetic Identity" and see a real sample transaction with the model's actual reasoning for flagging or clearing it.

---

## If a Judge Asks... (Quick Answers)

**"How do you know your synthetic data is realistic?"**
Every fake transaction is grounded in a per-user behavioral profile with realistic spending distributions (log-normal, matching real consumer spend patterns), and fraud is injected as a deliberate *deviation* from that profile — the same logic real fraud analysts use.

**"Why not just use a public fraud dataset?"**
Public datasets don't contain GenAI-specific attack patterns because those attacks are new; the challenge specifically asks us to build the generator, not just the detector.

**"What happens with real payment data instead of synthetic?"**
The feature engineering (velocity, deviation, account age, category norms) uses signals already standard in the payments industry, so the same pipeline would work on real data — you'd just need to retrain on real historical fraud examples instead of our synthetic ones.

**"What's actually novel here, versus a standard fraud classifier?"**
The closed feedback loop: the system automatically converts its own detection failures into new, harder training examples without a human manually deciding what new fraud pattern to test against.

**"What would you build next with more time?"**
The 4 documented-but-unsimulated attacks (deepfake voice, phishing, chargeback fraud, biometric spoofing) would need text/audio/image models rather than tabular data — a natural next phase.
