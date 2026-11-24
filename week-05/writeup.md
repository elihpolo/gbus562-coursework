## What I Built

I built a multi-agent supplier-response team consisting of a supply analyst, supplier writer, customer writer, and reviewer. I implemented both a fixed pipeline and an orchestrator that decides which specialists are needed. I added the --org option, dynamic CSV column mapping, and separate company draft folders to make the system work for both Brookfield Bikes and Copperline Coffee Machines.

I ran all four Copperline supplier emails through both coordinators and saved all eight runs. The pipeline used 51,441 tokens, while the orchestrator used 69,871 tokens. Although the orchestrator used more tokens overall, it was more efficient when it recognized that no specialists were needed.

## Why This Approach

Task A: Agent — The agent can determine which order and warranty information it needs to look up before drafting an appropriate response to the customer.

Task B: Team — Multiple specialists can identify affected machines, draft individual customer notices, prepare a regulatory report, and review the information for accuracy.

Task C: Pipeline — Every wholesale order follows the same sequence of steps, making a fixed workflow more consistent and efficient.

Task D: Orchestrator — Different types of emails require different specialists. An orchestrator can determine which specialists are needed based on the situation rather than following the same workflow every time.

## Example Run

```text

=== HANDOFF  coordinator -> all specialists  |  company folder and CSV columns found from the header rows ===
{
  "company_folder": "C:\\Users\\eli\\GBUS562\\gbus562-coursework\\week-05\\copperline-coffee",
  "drafts_folder": "C:\\Users\\eli\\GBUS562\\gbus562-coursework\\week-05\\drafts\\copperline-coffee",
  "columns": {
    "orders.csv": {
      "late_penalty": "late_penalty",
      "contact_email": "contact_email",
      "customer": "customer",
      "order_id": "order_id",
      "product": "product",
      "ship_day": "ship_by_day",
      "quantity": "units"
    },
    "bill-of-materials.csv": {
      "part_id": "part_id",
      "per_unit": "per_unit",
      "product": "product"
    },
    "parts.csv": {
      "part_id": "part_id",
      "description": "description",
      "on_hand": "on_hand",
      "supplier": "supplier"
    },
    "inbound.csv": {
      "arrives_in_days": "arrives_in_days",
      "po_number": "po_number",
      "part_id": "part_id",
      "supplier": "supplier",
      "quantity": "qty"
    },
    "suppliers.csv": {
      "contact_email": "contact_email",
      "contact_name": "contact_name",
      "part_id": "part_id",
      "supplier": "supplier"
    }
  }
}

##### STEP 1: supply analyst #####

=== HANDOFF  coordinator -> analyst  |  supplier email ===
From: Diane Kessler <d.kessler@danforthpump.example>
To: Purchasing <purchasing@copperlinecoffee.example>
Subject: PO-5512 - PU-20 pumps - partial shipment

Hello,

I'm writing about PO-5512 for 200 PU-20 vibration pumps. A test rig on our
assembly line failed inspection, and we can't release the full order on the
scheduled date.

We can deliver 40 of the 200 pumps on the scheduled date. The other 160 will
follow 15 days later.

We're sorry for the disruption. To help us plan, could you send us a list of
the customer orders these pumps are for, with each customer's name and
quantity? We'll do our best to keep the delay as short as we can.

Diane Kessler
Key Accounts, Danforth Pump Works

[tokens] analyst: in=1786 out=141

=== HANDOFF  analyst -> supply tool  |  call 1/10: get_part ===
{
  "part_id": "PU-20"
}

=== HANDOFF  supply tool -> analyst  |  result of call 1 ===
{
  "part_id": "PU-20",
  "description": "Vibration pump",
  "supplier": "Danforth Pump Works",
  "on_hand": 50,
  "scheduled_shipments": [
    {
      "po_number": "PO-5512",
      "supplier": "Danforth Pump Works",
      "qty": 200,
      "arrives_in_days": 4
    }
  ],
  "products_using_part": [
    {
      "product": "Cafe One",
      "parts_per_unit": 1
    },
    {
      "product": "Cafe Duo",
      "parts_per_unit": 2
    }
  ]
}

=== HANDOFF  analyst -> supply tool  |  call 2/10: get_orders_for_part ===
{
  "part_id": "PU-20"
}

=== HANDOFF  supply tool -> analyst  |  result of call 2 ===
{
  "part_id": "PU-20",
  "orders": [
    {
      "order_id": "O-2201",
      "customer": "Morning Ritual Cafe",
      "product": "Cafe One",
      "units_ordered": 20,
      "parts_per_unit": 1,
      "units_needed": 20,
      "ship_in_days": 6,
      "late_penalty": "no"
    },
    {
      "order_id": "O-2202",
      "customer": "Harbor Hotel Group",
      "product": "Cafe Duo",
      "units_ordered": 15,
      "parts_per_unit": 2,
      "units_needed": 30,
      "ship_in_days": 9,
      "late_penalty": "no"
    },
    {
      "order_id": "O-2203",
      "customer": "Elm State University Din... [1192 more characters]
[tokens] analyst: in=3023 out=166

=== HANDOFF  analyst -> supply tool  |  call 3/10: check_coverage ===
{
  "part_id": "PU-20",
  "arrivals": [
    {
      "qty": 40,
      "day": 4
    },
    {
      "qty": 160,
      "day": 19
    }
  ]
}

=== HANDOFF  supply tool -> analyst  |  result of call 3 ===
{
  "part_id": "PU-20",
  "on_hand": 50,
  "arrivals_used": [
    {
      "qty": 40,
      "day": 4
    },
    {
      "qty": 160,
      "day": 19
    }
  ],
  "total_supply": 250,
  "total_units_needed": 184,
  "orders": [
    {
      "order_id": "O-2201",
      "customer": "Morning Ritual Cafe",
      "units_needed": 20,
      "ship_in_days": 6,
      "late_penalty": "no",
      "covered": true,
      "units_short": 0,
      "first_ship_day": 6,
      "days_late": 0,
      "units_never_covered": 0
    },
    {
      "order_id": "O-2202",
      "customer": "Harbor Hotel Group",
      "units_n... [1743 more characters]
[tokens] analyst: in=4236 out=547

=== HANDOFF  analyst -> coordinator  |  brief (full) ===
{
  "part_id": "PU-20",
  "what_changed": "Of the 200 PU-20 pumps on PO-5512, only 40 will arrive on day 4 as scheduled, with the remaining 160 now arriving on day 19 instead of day 4.",
  "orders_at_risk": [
    {
      "order_id": "O-2203",
      "customer": "Elm State University Dining",
      "units_short": 10,
      "ship_day": 12,
      "ready_day": 19,
      "late_penalty": "yes"
    },
    {
      "order_id": "O-2204",
      "customer": "Kettle & Crumb Bakery",
      "units_short": 20,
      "ship_day": 15,
      "ready_day": 19,
      "late_penalty": "no"
    },
    {
      "order_id": "O-2205",
      "customer": "Tall Pines Coffee House",
      "units_short": 25,
      "ship_day": 17,
      "ready_day": 19,
      "late_penalty": "yes"
    }
  ],
  "options": [],
  "decisions_for_a_person": [
    "Decide whether to expedite or source PU-20 pumps elsewhere to cover O-2203 and O-2205, which carry late penalties, given they will now ship 7 and 2 days late respectively.",
    "Decide how to handle O-2204, which will ship 4 days late (no penalty, but customer should be informed)."
  ],
  "supplier_questions": [
    "Diane Kessler asked for a list of the customer orders these pumps are for, with each customer's name and quantity."
  ]
}

##### STEP 2: customer notices (3 order(s) at risk) #####

=== HANDOFF  coordinator -> customer_writer  |  facts for order O-2203 ===
Order facts:
{
  "order_id": "O-2203",
  "customer": "Elm State University Dining",
  "product": "Cafe One",
  "units_ordered": "50",
  "days_later_than_planned": 7
}
[tokens] customer_writer: in=299 out=225

=== HANDOFF  customer_writer -> coordinator  |  draft ===
Dear Elm State University Dining,

We're writing to update you on order O-2203 for 50 units of the Cafe One espresso machine. This order is now expected to ship 7 days later than originally planned.

We apologize for this delay. It is due to a delay in a part from one of our suppliers.

We understand the timing of this order matters to you, and we appreciate your patience as we work to get your machines shipped as soon as possible. We will keep you informed if there is any further update to the schedule.

If you have questions about your account or order terms, a member of our team will be glad to assist you directly.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines

=== HANDOFF  coordinator -> reviewer  |  draft to a customer ===
This draft goes to a customer.

Facts the draft was written from:
{
  "order_id": "O-2203",
  "customer": "Elm State University Dining",
  "product": "Cafe One",
  "units_ordered": "50",
  "days_later_than_planned": 7
}

Draft:
Dear Elm State University Dining,

We're writing to update you on order O-2203 for 50 units of the Cafe One espresso machine. This order is now expected to ship 7 days later than originally planned.

We apologize for this delay. It is due to a delay in a part from one of our suppliers.

We understand the timing of this order matters to you, and we appreciate your patience as we work to get your machines shipped as soon as possible. We will keep you informed if there is any further update to the schedule.

If you have questions about your account or order terms, a member of our team will be glad to assist you directly.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines
[tokens] reviewer: in=629 out=300

=== HANDOFF  reviewer -> coordinator  |  verdict ===
{
  "verdict": "APPROVE",
  "reasons": ""
}

FINAL DRAFT TO CUSTOMER O-2203
Dear Elm State University Dining,

We're writing to update you on order O-2203 for 50 units of the Cafe One espresso machine. This order is now expected to ship 7 days later than originally planned.

We apologize for this delay. It is due to a delay in a part from one of our suppliers.

We understand the timing of this order matters to you, and we appreciate your patience as we work to get your machines shipped as soon as possible. We will keep you informed if there is any further update to the schedule.

If you have questions about your account or order terms, a member of our team will be glad to assist you directly.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines
Marked for a person: yes

=== HANDOFF  coordinator -> person  |  saved customer-notice-O-2203.txt ===
{
  "file": "C:\\Users\\eli\\GBUS562\\gbus562-coursework\\week-05\\drafts\\copperline-coffee\\customer-notice-O-2203.txt",
  "recipient": "customer",
  "review": {
    "verdict": "APPROVE",
    "reasons": ""
  },
  "revisions": 0,
  "name_check_hits": [],
  "needs_a_person": true,
  "reasons": [
    "the order has a late penalty"
  ]
}

=== HANDOFF  coordinator -> customer_writer  |  facts for order O-2204 ===
Order facts:
{
  "order_id": "O-2204",
  "customer": "Kettle & Crumb Bakery",
  "product": "Cafe Duo",
  "units_ordered": "10",
  "days_later_than_planned": 4
}
[tokens] customer_writer: in=306 out=157

=== HANDOFF  customer_writer -> coordinator  |  draft ===
Subject: Update on Your Order O-2204

Dear Kettle & Crumb Bakery,

We're writing to update you on order O-2204 for 10 Cafe Duo units. The order is now expected to ship 4 days later than originally planned.

We apologize for the delay. It is due to a delay in a part from one of our suppliers.

We appreciate your patience and will keep you informed of any further updates regarding your order.

Customer Service, Copperline Coffee Machines

=== HANDOFF  coordinator -> reviewer  |  draft to a customer ===
This draft goes to a customer.

Facts the draft was written from:
{
  "order_id": "O-2204",
  "customer": "Kettle & Crumb Bakery",
  "product": "Cafe Duo",
  "units_ordered": "10",
  "days_later_than_planned": 4
}

Draft:
Subject: Update on Your Order O-2204

Dear Kettle & Crumb Bakery,

We're writing to update you on order O-2204 for 10 Cafe Duo units. The order is now expected to ship 4 days later than originally planned.

We apologize for the delay. It is due to a delay in a part from one of our suppliers.

We appreciate your patience and will keep you informed of any further updates regarding your order.

Customer Service, Copperline Coffee Machines
[tokens] reviewer: in=577 out=340

=== HANDOFF  reviewer -> coordinator  |  verdict ===
{
  "verdict": "APPROVE",
  "reasons": ""
}

FINAL DRAFT TO CUSTOMER O-2204
Subject: Update on Your Order O-2204

Dear Kettle & Crumb Bakery,

We're writing to update you on order O-2204 for 10 Cafe Duo units. The order is now expected to ship 4 days later than originally planned.

We apologize for the delay. It is due to a delay in a part from one of our suppliers.

We appreciate your patience and will keep you informed of any further updates regarding your order.

Customer Service, Copperline Coffee Machines
Marked for a person: no

=== HANDOFF  coordinator -> person  |  saved customer-notice-O-2204.txt ===
{
  "file": "C:\\Users\\eli\\GBUS562\\gbus562-coursework\\week-05\\drafts\\copperline-coffee\\customer-notice-O-2204.txt",
  "recipient": "customer",
  "review": {
    "verdict": "APPROVE",
    "reasons": ""
  },
  "revisions": 0,
  "name_check_hits": [],
  "needs_a_person": false,
  "reasons": []
}

=== HANDOFF  coordinator -> customer_writer  |  facts for order O-2205 ===
Order facts:
{
  "order_id": "O-2205",
  "customer": "Tall Pines Coffee House",
  "product": "Cafe One",
  "units_ordered": "25",
  "days_later_than_planned": 2
}
[tokens] customer_writer: in=302 out=199

=== HANDOFF  customer_writer -> coordinator  |  draft ===
Subject: Update on Your Order O-2205

Dear Tall Pines Coffee House,

We're writing to update you on order O-2205 for 25 units of the Cafe One.

Your order is now expected to ship 2 days later than originally planned. We apologize for the delay.

This is due to a delay in a part from one of our suppliers. We understand timing matters for your business and appreciate your patience as we work to get your order out as soon as possible.

If you have any questions in the meantime, please don't hesitate to reach out.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines

=== HANDOFF  coordinator -> reviewer  |  draft to a customer ===
This draft goes to a customer.

Facts the draft was written from:
{
  "order_id": "O-2205",
  "customer": "Tall Pines Coffee House",
  "product": "Cafe One",
  "units_ordered": "25",
  "days_later_than_planned": 2
}

Draft:
Subject: Update on Your Order O-2205

Dear Tall Pines Coffee House,

We're writing to update you on order O-2205 for 25 units of the Cafe One.

Your order is now expected to ship 2 days later than originally planned. We apologize for the delay.

This is due to a delay in a part from one of our suppliers. We understand timing matters for your business and appreciate your patience as we work to get your order out as soon as possible.

If you have any questions in the meantime, please don't hesitate to reach out.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines
[tokens] reviewer: in=615 out=342

=== HANDOFF  reviewer -> coordinator  |  verdict ===
{
  "verdict": "APPROVE",
  "reasons": ""
}

FINAL DRAFT TO CUSTOMER O-2205
Subject: Update on Your Order O-2205

Dear Tall Pines Coffee House,

We're writing to update you on order O-2205 for 25 units of the Cafe One.

Your order is now expected to ship 2 days later than originally planned. We apologize for the delay.

This is due to a delay in a part from one of our suppliers. We understand timing matters for your business and appreciate your patience as we work to get your order out as soon as possible.

If you have any questions in the meantime, please don't hesitate to reach out.

Thank you for your understanding.

Customer Service, Copperline Coffee Machines
Marked for a person: yes

=== HANDOFF  coordinator -> person  |  saved customer-notice-O-2205.txt ===
{
  "file": "C:\\Users\\eli\\GBUS562\\gbus562-coursework\\week-05\\drafts\\copperline-coffee\\customer-notice-O-2205.txt",
  "recipient": "customer",
  "review": {
    "verdict": "APPROVE",
    "reasons": ""
  },
  "revisions": 0,
  "name_check_hits": [],
  "needs_a_person": true,
  "reasons": [
    "the order has a late penalty"
  ]
}

##### STEP 3: supplier reply #####

=== HANDOFF  coordinator -> supplier_writer  |  inputs with customer names removed ===
Supplier's email:

From: Diane Kessler <d.kessler@danforthpump.example>
To: Purchasing <purchasing@copperlinecoffee.example>
Subject: PO-5512 - PU-20 pumps - partial shipment

Hello,

I'm writing about PO-5512 for 200 PU-20 vibration pumps. A test rig on our
assembly line failed inspection, and we can't release the full order on the
scheduled date.

We can deliver 40 of the 200 pumps on the scheduled date. The other 160 will
follow 15 days later.

We're sorry for the disruption. To help us plan, could you send us a list of
the customer orders these pumps are for, with each customer's name and
quantity? We'll do our best to keep the delay as short as we can.

Diane Kessler
Key Accounts, Danforth Pump Works


Analyst's brief (JSON):
{
  "part_id": "PU-20",
  "what_changed": "Of the 200 PU-20 pumps on PO-5512, only 40 will arrive on day 4 as scheduled, with the remaining 160 now arriving on day 19 instead of day 4.",
  "orders_at_risk": [
    {
      "order_id": "O-2203",
      "units_short": 10,
      "ship_day": 12,
      "ready_day": 19,
      "late_penalty": "yes"
    },
    {
      "order_id": "O-2204",
      "units_short": 20,
      "ship_day": 15,
      "ready_day": 19,
      "late_penalty": "no"
    },
    {
      "order_id": "O-2205",
      "units_short": 25,
      "ship_day": 17,
      "ready_day": 19,
      "late_penalty": "yes"
    }
  ],
  "options": [],
  "decisions_for_a_person": [
    "Decide whether to expedite or source PU-20 pumps elsewhere to cover O-2203 and O-2205, which carry late penalties, given they will now ship 7 and 2 days late respectively.",
    "Decide how to handle O-2204, which will ship 4 days late (no penalty, but customer should be informed)."
  ],
  "supplier_questions": [
    "Diane Kessler asked for a list of the customer orders these pumps are for, with each customer's name and quantity."
  ]
}
[tokens] supplier_writer: in=1064 out=363

=== HANDOFF  supplier_writer -> coordinator  |  draft ===
Subject: RE: PO-5512 - PU-20 pumps - partial shipment

Hello Diane,

Thank you for the update. To confirm our understanding: of the 200 PU-20 pumps on PO-5512, 40 will arrive on day 4 as scheduled, with the remaining 160 now arriving on day 19 instead of day 4 — a 15-day delay on that portion.

This shortfall affects three of our outbound orders, totaling 55 units short across them, with delays ranging from 2 to 7 days versus their required ship dates. This has real impact on our side, including penalty exposure on two of the affected orders.

We are not able to share customer names or details — that information is internal. We can tell you the impact is material enough that we need to minimize the delay wherever possible.

Please let us know what options exist to expedite any portion of the 160 units sooner, even in smaller partial shipments ahead of day 19. Any acceleration would directly reduce our exposure.

We will confirm our decision on how to proceed by the time you need it.

Best regards,
Purchasing, Copperline Coffee Machines

=== HANDOFF  coordinator -> reviewer  |  draft to a supplier ===
This draft goes to a supplier.

Facts the draft was written from:
{
  "supplier_email": "From: Diane Kessler <d.kessler@danforthpump.example>\nTo: Purchasing <purchasing@copperlinecoffee.example>\nSubject: PO-5512 - PU-20 pumps - partial shipment\n\nHello,\n\nI'm writing about PO-5512 for 200 PU-20 vibration pumps. A test rig on our\nassembly line failed inspection, and we can't release the full order on the\nscheduled date.\n\nWe can deliver 40 of the 200 pumps on the scheduled date. The other 160 will\nfollow 15 days later.\n\nWe're sorry for the disruption. To help us plan, could you send us a list of\nthe customer orders these pumps are for, with each customer's name and\nquantity? We'll do our best to keep the delay as short as we can.\n\nDiane Kessler\nKey Accounts, Danforth Pump Works\n",
  "analyst_brief": {
    "part_id": "PU-20",
    "what_changed": "Of the 200 PU-20 pumps on PO-5512, only 40 will arrive on day 4 as scheduled, with the remaining 160 now arriving on day 19 instead of day 4.",
    "orders_at_risk": [
      {
        "order_id": "O-2203",
        "units_short": 10,
        "ship_day": 12,
        "ready_day": 19,
        "late_penalty": "yes"
      },
      {
        "order_id": "O-2204",
        "units_short": 20,
        "ship_day": 15,
        "ready_day": 19,
        "late_penalty": "no"
      },
      {
        "order_id": "O-2205",
        "units_short": 25,
        "ship_day": 17,
        "ready_day": 19,
        "late_penalty": "yes"
      }
    ],
    "options": [],
    "decisions_for_a_person": [
      "Decide whether to expedite or source PU-20 pumps elsewhere to cover O-2203 and O-2205, which carry late penalties, given they will now ship 7 and 2 days late respectively.",
      "Decide how to handle O-2204, which will ship 4 days late (no penalty, but customer should be informed)."
    ],
    "supplier_questions": [
      "Diane Kessler asked for a list of the customer orders these pumps are for, with each customer's name and quantity."
    ]
  }
}

Draft:
Subject: RE: PO-5512 - PU-20 pumps - partial shipment

Hello Diane,

Thank you for the update. To confirm our understanding: of the 200 PU-20 pumps on PO-5512, 40 will arrive on day 4 as scheduled, with the remaining 160 now arriving on day 19 instead of day 4 — a 15-day delay on that portion.

This shortfall affects three of our outbound orders, totaling 55 units short across them, with delays ranging from 2 to 7 days versus their required ship dates. This has real impact on our side, including penalty exposure on two of the affected orders.

We are not able to share customer names or details — that information is internal. We can tell you the impact is material enough that we need to minimize the delay wherever possible.

Please let us know what options exist to expedite any portion of the 160 units sooner, even in smaller partial shipments ahead of day 19. Any acceleration would directly reduce our exposure.

We will confirm our decision on how to proceed by the time you need it.

Best regards,
Purchasing, Copperline Coffee Machines
[tokens] reviewer: in=1521 out=499

=== HANDOFF  reviewer -> coordinator  |  verdict ===
{
  "verdict": "APPROVE",
  "reasons": ""
}

FINAL DRAFT TO SUPPLIER
Subject: RE: PO-5512 - PU-20 pumps - partial shipment

Hello Diane,

Thank you for the update. To confirm our understanding: of the 200 PU-20 pumps on PO-5512, 40 will arrive on day 4 as scheduled, with the remaining 160 now arriving on day 19 instead of day 4 — a 15-day delay on that portion.

This shortfall affects three of our outbound orders, totaling 55 units short across them, with delays ranging from 2 to 7 days versus their required ship dates. This has real impact on our side, including penalty exposure on two of the affected orders.

We are not able to share customer names or details — that information is internal. We can tell you the impact is material enough that we need to minimize the delay wherever possible.

Please let us know what options exist to expedite any portion of the 160 units sooner, even in smaller partial shipments ahead of day 19. Any acceleration would directly reduce our exposure.

We will confirm our decision on how to proceed by the time you need it.

Best regards,
Purchasing, Copperline Coffee Machines
Marked for a person: no

=== HANDOFF  coordinator -> person  |  saved supplier-reply-PU-20.txt ===
{
  "file": "C:\\Users\\eli\\GBUS562\\gbus562-coursework\\week-05\\drafts\\copperline-coffee\\supplier-reply-PU-20.txt",
  "recipient": "supplier",
  "review": {
    "verdict": "APPROVE",
    "reasons": ""
  },
  "revisions": 0,
  "name_check_hits": [],
  "needs_a_person": false,
  "reasons": []
}

##### SUMMARY #####
Drafts saved: 4
  C:\Users\eli\GBUS562\gbus562-coursework\week-05\drafts\copperline-coffee\customer-notice-O-2203.txt
  C:\Users\eli\GBUS562\gbus562-coursework\week-05\drafts\copperline-coffee\customer-notice-O-2204.txt
  C:\Users\eli\GBUS562\gbus562-coursework\week-05\drafts\copperline-coffee\customer-notice-O-2205.txt
  C:\Users\eli\GBUS562\gbus562-coursework\week-05\drafts\copperline-coffee\supplier-reply-PU-20.txt
Drafts marked for a person: 2
  customer-notice-O-2203.txt: the order has a late penalty
  customer-notice-O-2205.txt: the order has a late penalty
Decisions for a person: 2
  - Decide whether to expedite or source PU-20 pumps elsewhere to cover O-2203 and O-2205, which carry late penalties, given they will now ship 7 and 2 days late respectively.
  - Decide how to handle O-2204, which will ship 4 days late (no penalty, but customer should be informed).

=== TOKENS BY SPECIALIST ===
specialist         calls     input    output     total
analyst                3      9045       854      9899
customer_writer        3       907       581      1488
reviewer               4      3342      1481      4823
supplier_writer        1      1064       363      1427
all                   11     14358      3279     17637
Total tokens: 17637 (input 14358, output 3279)
```

## Reflection

Email 1 reading: Matches — Diane stated that the remaining 160 pumps would arrive 15 days after the scheduled date. Since the original arrival was day 4, the analyst correctly identified day 19 as the revised arrival date.

Email 1 customer names: No — The supplier reply declined to share customer names or individual order details and instead provided an aggregate summary of the affected orders and delays.

Email 4 orchestrator: None — The orchestrator went directly to finish because the supplier confirmed that the order was unaffected. The pipeline still called the supply analyst and supplier writer before determining that no customer notices or supplier reply were needed. The orchestrator used 1,675 tokens compared with 8,548 for the pipeline.
