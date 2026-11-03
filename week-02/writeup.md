## What I Built

For Week 2, I built a Prompt Lab, a chat tool that runs in a web browser. The prompt lab is built in one HTML file called `prompt-lab.html`. On the left side, I can enter my API key, set a system prompt, and type a message. The conversation then shows up on the right side. It uses the `claude-sonnet-5` model, and my API key isn't saved, so I have to enter it each time.

Once I got the Prompt Lab working, I used it to complete four different tasks for Wildframe Coffee Roasters, a specialty coffee company. I tested different prompting techniques and exported each conversation into a Markdown file in the `runs` folder.

## Why This Approach

Task 1 - Technique: zero-shot

I used zero-shot for this task because I wanted Claude to come up with creative subscriber perks without giving it examples to follow. I gave cluade instructions and formatting requirements, and it came back with six ideas that followed the format. I didn't need a follow-up, but I did notice one issue. The third perk was called "annual" even though it said it would be delivered every six months.

Task 2 - Technique: one-shot

For task 2, I used one-shot because I wanted the new coffee cards to match an example that was already provided. I gave Claude one example that helped it format and the writing style. It followed the format well, but it forgot to include low acidity in the Cerrado coffee description. I followed up and asked it to add that while keeping everything else the same, and it made the correction.


Task 3 - Technique: few-shot

I used few-shot prompting because I wanted Claude to see a few examples of how Wildframe responds to customers. I gave it three examples to help it understand the company's writing style. Claude did a good job matching the tone, but it also included some information that wasn't confirmed, such as a specific decaf coffee and an update about a shipping issue. I asked Claude to fix those mistakes, and it corrected some of them, but there were still a few statements that weren't confirmed. This helped me understand that giving examples can improve the response, but it doesn't mean everything will be correct.

Task 4 - Technique: chain-of-thought

For the last task, I used chain-of-thought prompting because Claude needed to compare three locations and calculate which one would be the best choice. I wanted it to show the calculations so I could check the numbers myself. Claude recommended Riverside Farmers Market because it was within the $5,000 budget and had the highest revenue after subtracting rent. I had to send a follow-up because the first response included emojis and formatting I didn't want. I also noticed that Claude called the final amount "profit," even though it didn't include other business expenses.

## Example Run

```text
claude-sonnet-5

### System
You are helping Wildframe Coffee Roasters, a specialty coffee company that sells beans online and through monthly subscriptions. The brand voice is warm, plainspoken, and a little irreverent, without corporate jargon. Its customers are environmentally conscious urban professionals.

### You
Wildframe Coffee Roasters is adding three new coffees to its shop. I want you to create a bean card for each one using the same format and writing style as our existing card.

Here is an example from our Brand Kit:

HUILA, COLOMBIA
Roast: Medium
Tastes like: red apple, brown sugar, cocoa
Brew it: Pour-over or drip
Real talk: The coffee that converted our office's tea drinker. Mostly.

Now create cards for these three coffees:

1. Yirgacheffe, Ethiopia — Light roast, jasmine, lemon, bergamot, best for pour-over.
2. Cerrado, Brazil — Medium-dark roast, peanut, milk chocolate, low acidity, good for espresso or French press.
3. Chiapas, Mexico — Medium roast, almond, caramel, orange peel, good for drip or AeroPress.

Make sure each card follows the exact same labels and order as the example: coffee name and origin, Roast, Tastes like, Brew it, and Real talk. Keep the Real talk descriptions short and in Wildframe's voice.

### Claude
YIRGACHEFFE, ETHIOPIA
Roast: Light
Tastes like: jasmine, lemon, bergamot
Brew it: Pour-over
Real talk: Smells like a flower shop, tastes like you made a good life choice this morning.

CERRADO, BRAZIL
Roast: Medium-dark
Tastes like: peanut, milk chocolate
Brew it: Espresso or French press
Real talk: Low acid, high comfort. The coffee equivalent of a weighted blanket.

CHIAPAS, MEXICO
Roast: Medium
Tastes like: almond, caramel, orange peel
Brew it: Drip or AeroPress
Real talk: Balanced, friendly, a little citrusy. The golden retriever of our lineup.

### You
These look good! Can you keep everything the same but add low acidity to the Tastes like line for Cerrado, Brazil? Please resend all three complete cards in the same format.

### Claude
YIRGACHEFFE, ETHIOPIA
Roast: Light
Tastes like: jasmine, lemon, bergamot
Brew it: Pour-over
Real talk: Smells like a flower shop, tastes like you made a good life choice this morning.

CERRADO, BRAZIL
Roast: Medium-dark
Tastes like: peanut, milk chocolate, low acidity
Brew it: Espresso or French press
Real talk: Low acid, high comfort. The coffee equivalent of a weighted blanket.

CHIAPAS, MEXICO
Roast: Medium
Tastes like: almond, caramel, orange peel
Brew it: Drip or AeroPress
Real talk: Balanced, friendly, a little citrusy. The golden retriever of our lineup.
```

## Reflection

After completing all four tasks, I learned that different prompting techniques can be useful depending on what you want Claude to do. I think using examples worked best when I wanted Claude to follow a certain format or writing style. For example, one-shot worked well for creating the coffee cards, while few-shot helped Claude understand how to respond to different customers.

One of the biggest things I noticed was that Claude can follow most of the instructions but still make mistakes. In Task 2, it left out information about one of the coffees, and in Task 3, it included details that weren't confirmed. Even after asking Claude to fix some of these problems, there were still a few mistakes. This showed me that I need to review the responses instead of assuming everything is correct.

I am still unsure whether zero-shot was the best choice for Task 1. It gave Claude more freedom to come up with ideas, but providing an example might have helped make the ideas more realistic. I think it would be interesting to try both methods and compare the results.
