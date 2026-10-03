# LoanWatch — Sample Questions

These questions are pre-loaded in the Streamlit app's **Sample Questions** page.
Click any button to run it live through the Cortex Agent.

## Demo questions (verified queries)

These map to verified queries (VQRs) in the semantic view and produce consistent, governed answers.

1. Which borrowers over 50 lakh show early-warning signals this quarter?
2. Why is Meera Traders flagged?
3. Show the transactions between Meera Traders and its related parties in the last 6 months.
4. What is our provisioning impact this month, and which accounts drove it?
5. How many SMA-2 accounts do we have?
6. Within how many days must a Red Flagged Account be reported on CRILC?
7. How does our gross NPA ratio compare to the system-wide ratio?
8. What are the system-wide bank fraud statistics for FY26?

## Ask anything (generated live)

These have no verified query — Cortex Analyst generates SQL on the fly from the semantic view.

1. Which borrowers in Karnataka have a GST-to-bank gap above 50%?
2. List loans that moved from SMA-1 to SMA-2 in September 2026.
3. Which borrowers paid EMIs from inflows received the same day from another bank?
4. Show all counterparties that share a director with Nandi Infra.
5. What is the total exposure of borrowers with two or more early-warning signals?
6. Which branch has the highest number of open signals?

## RBI rules (answered from loaded directions with paragraph citations)

These route to Cortex Search over the 4 parsed RBI regulatory PDFs. Answers cite DOC_ID and paragraph number.

1. How long does a bank have to decide whether an RFA is fraud?
2. When can an NPA account be upgraded to standard?
3. What is the CTR threshold for cash transactions?
4. Is the 2016 Early Warning Signals list still in force?
