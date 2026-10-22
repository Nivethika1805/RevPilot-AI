# RevPilot AI — 3-Minute Executive Product Demonstration Script

**Target Duration:** 3:00 (180 Seconds)  
**Spoken Word Count:** ~450 Words (at a measured, professional 150 words/minute pace)  
**Speaker Persona:** Lead Solutions Architect & Product Designer  
**Target Audience:** VP of Sales, Chief Revenue Officer, RevOps Director  

---

### [0:00 - 0:30] Introduction & Command Center Overview

**On-Screen Action:**  
Start on the **Revenue Command Center** (`/`). Hover over the top bar showing the pinned horizon `Oct 20, 2026` and the `Synthetic Demo Data` badge. Point the cursor to the 5 executive metric cards ($2,968,000 open pipeline, 9 At-Risk Deals, 12 High-Urgency Conversations).

**Narrator Voiceover:**  
> *"Welcome to RevPilot AI — the evidence-driven revenue intelligence inbox for sales leadership.  
> 
> Most revenue platforms flash black-box AI scores that reps don't trust and managers can't defend. RevPilot is built on a different thesis: **Know what happened. Understand why it matters. Decide what to do next.**  
> 
> Right here on our Command Center, every metric is computed live from verified CRM records and conversation transcripts pinned to our October 2026 horizon. Notice our pipeline stands at $2.97 million across 18 open deals, with 9 opportunities flagged as High or Critical on our explainable, rule-based risk index."*

---

### [0:30 - 1:00] Deep-Dive: High-Risk Deal `DL-1001` & Source Evidence

**On-Screen Action:**  
Click the **At-Risk Deals** card or navigate to **Deals & Risk** (`/deals`). Click on deal **`DL-1001`** (`Global Fleet Intelligence Expansion`, $240,000). The Deal Cockpit opens. Scroll down to show the 8 risk signals and click on the `UNRESOLVED_PRICING_OBJECTION` signal chip. Point to the highlighted source evidence chip `CALL-2043#L2`.

**Narrator Voiceover:**  
> *"Let's drill into our highest-value stalled deal: `DL-1001`, a $240,000 expansion with Northwind Logistics.  
> 
> RevPilot assigns a Risk Index of 70. But look at why: this isn't an arbitrary prediction. We see two detected risk signals: an unresolved pricing objection and 21 days of customer silence.  
> 
> Clicking the pricing signal highlights the exact source evidence: Call `CALL-2043`, Line 2. The buyer stated verbatim: *'the price is too high compared to what we budgeted.'*  
> 
> Notice our alert controls on the right: resolving an alert acknowledges the manager's workflow, but it does not artificially manipulate the risk score until verified counter-evidence arrives."*

---

### [1:00 - 1:35] Explainable Routing & The Competing Precedence Decision

**On-Screen Action:**  
Navigate to **Routing Rules** (`/routing`). Scroll through the precedence-ordered rules. Click on the **Unassigned Review Queue** tab to show `CALL-2045`. Then open the **Findings & Evidence** page (`/findings`) and scroll to the **Difficult Routing Decision** section featuring conversation `EMAIL-2044`.

**Narrator Voiceover:**  
> *"Next: Explainable Routing. When deals advance, conversations must reach the right expert immediately.  
> 
> Take conversation `EMAIL-2044`, an urgent redline email from Northwind Finance. Two rules competed: Rule #1 for Senior Pricing Escalation and Rule #4 for Standard Account Executive routing.  
> 
> Rather than guessing or silently picking by internal ID, RevPilot’s deterministic precedence engine awarded the route to Marcus Vance, our Pricing Lead, because Rule #1 possessed higher priority order and greater condition specificity. And for tied rules with conflicting owners, conversations safely enter our Unassigned Review Queue."*

---

### [1:35 - 2:20] Idempotent Import, Provenance & Conflict Protection

**On-Screen Action:**  
Navigate to **Import & Corrections** (`/imports`).  
1. In the Import Wizard, upload `data/deals_v1.csv`. Click through Preview, Column Mapping, and Confirm. Show the report: 0 new, 20 unchanged records.  
2. Now switch to the **Pending Conflicts** tab. Show deal `DL-1005` where the manager manually corrected the stage to `Negotiation`. Show the incoming source file proposing `Proposal`. Click **Resolve Conflict** -> **Keep Current Manual Value**.

**Narrator Voiceover:**  
> *"Now let's examine RevPilot's data reliability engine. Sales systems ingest messy, conflicting CSVs daily.  
> 
> Watch what happens when I re-import `deals_v1.csv`: our 11-stage pipeline hashes each row. Result? Exactly zero duplicate rows and zero unnecessary database updates.  
> 
> Even better: on deal `DL-1005`, our manager manually corrected the stage to *Negotiation*. When an automated sync attempts to revert it, RevPilot protects the manual edit via field-level provenance, holding the manual value intact and surfacing a pending conflict for review. We can keep the manual edit, accept the source, or enter an agreed compromise."*

---

### [2:20 - 3:00] Verifiable Export Center & Closing

**On-Screen Action:**  
Navigate to **Export Center** (`/exports`). Select CSV format and all entities. Click **Generate Verifiable Export**. When generated, point out the record counts (134 total rows) and click **Verify**. The green badge confirms: `TAMPER: NONE — SHA-256 MATCH`. Click **Manifest** to preview `manifest.json`.

**Narrator Voiceover:**  
> *"Finally, the Export Center. Compliance teams require proof that data has not been altered.  
> 
> Every export package generates real files on disk, cleanses cells against formula injection, and writes a signed `manifest.json` with SHA-256 hashes. Clicking *Verify* re-reads the disk files byte-for-byte to confirm complete cryptographic integrity.  
> 
> RevPilot AI brings transparency, rigor, and evidence-driven discipline to revenue leadership. Thank you."*
