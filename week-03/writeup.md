# Week 3: RAG Tool for Finance Documents

## What I Built

For this assignment, I used Claude Code to build a RAG tool called ask.py that answers questions using information from company documents. The tool reads files such as PDFs, HTML, Markdown, and text documents, breaks them into smaller sections, and stores them in a database called ChromaDB. When I ask a question, it finds the five most relevant sections and sends them to Claude to create an answer based on that information. The goal is to have Claude use the actual documents instead of making up an answer.

I first tested the tool using five documents from Copperline Manufacturing. After getting it working, I switched to Larkfield Credit Union's documents and ran the required questions. I also added options to choose which folder to search and save the results to a text file. This made it easier to compare answers and see which documents Claude was using.

## Why This Approach

Chunking method: structure

Makes sense on its own: Yes. I decided to split the documents by their headings and sections because most of the information was already organized by topic. This made more sense to me than splitting everything into random sections based on word count. Each chunk also includes a heading so it is easier to understand on its own.

Label and source: Both. Each chunk includes the document title and section heading, along with the original filename. This helps Claude know where the information came from and makes it easier to check whether the answer matches the original document.

Short enough: Yes. I tried to keep each chunk around 160 words or less so the embedding model could read all of the information. The model has a 256-token limit, and the longest Larkfield chunk was only 123 words and 164 tokens. This helped prevent important information from being cut off.

## Example Run

Question 2, copied unedited from `runs/q2.txt`:

```text
Question: A member needs a replacement debit card quickly. What does rush delivery cost?
Documents: C:\Users\eli\GBUS562\gbus562-coursework\week-03\larkfield-docs
Model: claude-sonnet-5

RETRIEVED CHUNKS (top 5; similarity = 1 - cosine distance, higher = closer)

Rank 1 | similarity 0.584 | source: consumer-fee-schedule.html | section: ATM and debit card fees
    Larkfield Credit Union | Consumer Fee Schedule (Version 8, current)
    Section: ATM and debit card fees
    Withdrawals at Larkfield ATMs and at CO-OP network ATMs are free. A withdrawal at any other ATM costs $2, and the ATM's owner may charge its own fee as well. A replacement debit card costs $10, or $30 with rush delivery. A replacement card is free when the old card was reported lost or stolen because of fraud.

Rank 2 | similarity 0.501 | source: card-dispute-procedure.html | section: How much the member may have to pay
    Larkfield Credit Union | Debit Card Dispute Procedure (Version 4, current)
    Section: How much the member may have to pay
    A member's share of the loss from unauthorized debit card transactions depends on how quickly they report it. If the member reports a lost or stolen card within two business days of learning about it, they pay no more than $50. If they report it later than that, they may pay up to $500. If unauthorized transactions appear on a statement and the member does not report them within 60 days after the statement was sent, they may have to pay for transactions after those 60 days in full.

Rank 3 | similarity 0.461 | source: card-dispute-procedure.html | section: When a member reports a transaction they did not make
    Larkfield Credit Union | Debit Card Dispute Procedure (Version 4, current)
    Section: When a member reports a transaction they did not make
    When a member says a debit card transaction on their account was not made or authorized by them, freeze the card right away in the card system, then open a dispute case. Order a replacement card. The replacement is free when the card was used for fraud.

Rank 4 | similarity 0.414 | source: consumer-fee-schedule.html | section: Overdraft and returned item fees
    Larkfield Credit Union | Consumer Fee Schedule (Version 8, current)
    Section: Overdraft and returned item fees
    When Larkfield pays a check, debit card purchase, or automatic payment that overdraws a member's checking account, the overdraft fee is $29 per item paid. When Larkfield returns an item unpaid because the account does not have enough money, the returned item fee is $29 per item returned. No more than three overdraft or returned item fees are charged to one account in a single business day.
    No overdraft fee is charged if the account is overdrawn by $10 or less at the end of the business day.
    Members can link a savings account for overdraft transfers. An overdraft transfer from a linked savings account is free.

Rank 5 | similarity 0.398 | source: consumer-fee-schedule.html | section: Statements and account research
    Larkfield Credit Union | Consumer Fee Schedule (Version 8, current)
    Section: Statements and account research
    Electronic statements are free. Paper statements cost $2 per month. Account research, such as finding an old transaction or reconciling an account, costs $20 per hour with a one-hour minimum. A copy of a paid check costs $3.

ANSWER
Rush delivery of a replacement debit card costs **$30** (consumer-fee-schedule.html, "ATM and debit card fees").

Note: this $30 rate applies to the standard, non-fraud replacement scenario. If the card is being replaced because it was reported lost or stolen due to fraud, the replacement itself is free (consumer-fee-schedule.html, "ATM and debit card fees"; card-dispute-procedure.html, "When a member reports a transaction they did not make"), but the sources do not specify whether the rush delivery fee is also waived in that fraud scenario—that detail is not addressed in the documents.
```

## Reflection

What was wrong: The file consumer-fee-schedule-v7.html was an older version of Larkfield's fee schedule, but it was still included with the current documents. It listed the overdraft fee as $35, while the newer Version 8 document listed it as $29. When I asked Question 1, Claude found both versions and pointed out the difference. This showed me how having outdated information in the database can cause confusion even when the tool is working correctly.

How I fixed it: Moved the older Version 7 document into a separate archive folder so the tool would no longer search it. I then rebuilt the database with only the five current documents and ran Question 1 again. This time Claude correctly answered $29 and only used the current fee schedule. I kept the original results so I could compare the before and after answers.

Prevention: Archive process. I think the best way to prevent this problem is to make sure older versions of documents are removed from the active folder whenever a new version is added. The old documents can still be saved in a separate archive folder, but they should not be included when rebuilding the database. It would also help to check for duplicate document titles before adding new files.

Question 6: Declined. I asked Claude for the current 30-year fixed mortgage rate, but the documents did not include that information. The retrieved sections were about share certificates and account fees instead. Claude correctly said that the documents did not answer the question rather than guessing a mortgage rate. This showed me why it is important for a RAG tool to recognize when it does not have enough information to answer.

One other thing I noticed while testing was that Claude sometimes misunderstood a rule even when it found the correct document. For Question 4, it initially confused which manager needed to approve certain refunds. I updated the general instructions to make Claude check the exact conditions in the documents before answering. After testing it again, the answer was more accurate. This helped me understand that RAG can improve accuracy, but the answers still need to be checked.
