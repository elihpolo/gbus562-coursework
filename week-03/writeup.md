# Week 3: RAG Tool for Finance Documents

## What I Built

I built `ask.py`, a command-line retrieval-augmented generation (RAG) tool that answers questions from a folder of company documents. It reads HTML, PDF, Markdown, and text files, splits each document into chunks by section, and stores the chunks in a ChromaDB vector database. When I ask a question, it pulls the five closest chunks and sends them to Claude (`claude-sonnet-5`) with instructions to answer only from those sources and to cite the filename and section for every fact. If the documents don't cover the question, Claude is supposed to say so instead of guessing.

The `--docs` option picks which folder to search, and each folder gets its own database, which is kept out of Git. The `--save` option writes the whole run to a text file: the ranked chunks with similarity scores and filenames, then an `ANSWER` line, then Claude's answer. I first built it for Copperline Manufacturing's five finance documents (35 chunks). Then I used it on Larkfield Credit Union's documents, which is where the seven runs in `runs/` come from.

## Why This Approach

Chunking method: structure. Every document already has a title and clear section headings, and each section covers one topic, so I made each section one chunk instead of cutting the text every N words.

Makes sense on its own: Yes. Every chunk starts with a short header naming the organization, the document title and version, and the section heading. A chunk like "the limit includes tax and tip" still makes sense when it comes back by itself.

Label and source: Both. The document title and section heading are part of the text that gets embedded, and the source filename is stored as metadata. Claude sees the filename for every chunk and has to cite it.

Short enough: Yes. The embedding model (all-MiniLM-L6-v2) stops reading after 256 tokens, which is about 190 words. I aimed for 160 words per chunk, and the build checks every chunk with the model's own tokenizer and stops if any chunk is too long. The longest Larkfield chunk is 123 words (164 tokens), so nothing gets cut off.

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

What was wrong: consumer-fee-schedule-v7.html was an outdated copy of the Consumer Fee Schedule that was still in the active folder, and it still called itself "Version 7 (current)." For Question 1, it listed a $35 overdraft fee, while the real current schedule (Version 8, consumer-fee-schedule.html) says $29. Both chunks came back as the top two results, so Claude correctly flagged the conflict but couldn't tell me which fee was real (`runs/q1-before.txt`).

How I fixed it: Moved consumer-fee-schedule-v7.html out of larkfield-docs and into a separate larkfield-docs-archive folder without editing it, then rebuilt the Larkfield database so it only had the five active documents (30 chunks instead of 39). When I ran Question 1 again with the same wording, it gave only the $29 fee, cited consumer-fee-schedule.html, and none of the retrieved chunks came from Version 7 (`runs/q1-after.txt`).

Prevention: Archive process. Whenever a new version of a policy is published, the old version should be moved to an archive folder that the tool never indexes, and the database should be rebuilt right away. Before each build, someone should also check that no two documents share the same title, since a duplicate title usually means an old version was left behind.

Question 6: Declined. The question asked for the current 30-year fixed mortgage rate, but the five retrieved chunks were only about share certificates (dividend rates, terms, and maturity) and account fees. None of the Larkfield documents mention mortgages, so Claude said the documents do not answer the question and did not make up a rate (`runs/q6.txt`).
