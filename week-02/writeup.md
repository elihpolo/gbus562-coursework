## What I Built

For Week 2, I used Claude Code to build a Prompt Lab, a simple chat tool that runs in a web browser. Everything is in one HTML file called `prompt-lab.html`. On the left side of the page, I can enter my API key, write a system prompt, and type my message, and the conversation appears on the right. The lab uses the `claude-sonnet-5` model. My API key isn't saved in the file or in the exports, so I enter it again each session.

After testing the lab with my Anthropic API key, I used it to complete four different tasks for Wildframe Coffee Roasters, a specialty coffee company. I exported each conversation as a Markdown file and saved them in the `runs` folder.

## Why This Approach

Task 1 - Technique: zero-shot

Zero-shot made sense because I wanted creative ideas for subscriber perks, and an example might have pushed Claude toward ideas similar to mine. I gave it the task and clear format limits instead, and it came back with six ideas in the right format, so I didn't send a follow-up. I did notice that the third perk is called "annual" but says it's delivered every 6 months, which shows that a well-formatted answer still needs to be checked.

Task 2 - Technique: one-shot

One-shot fit this task because the new bean cards needed to match an existing card, and one example was enough to show the format and style. Claude followed the labels and order correctly, and the Real talk lines sounded like Wildframe. However, it left low acidity out of the Tastes like line for the Cerrado coffee, so I asked it to add that and resend all three cards. It made that change and kept everything else the same.

Task 3 - Technique: few-shot

I used few-shot because brand voice is harder to explain than a card format, and the customer comments called for different kinds of replies. Three examples showed how Wildframe handles a skeptical question, a complaint, and a compliment, and the tone of Claude's replies matched them well. Even though I told it not to make unconfirmed promises, the first draft mentioned a Swiss Water decaf and said the shipping issue was already being looked into, so I asked it to remove those details. The new version fixed those two problems, but it still promised the order would arrive "pronto" and said Wildframe has a decaf it's proud of, so the examples helped more with tone than with following that rule.

Task 4 - Technique: chain-of-thought

Chain-of-thought made sense because choosing a location depended on several calculations, and I wanted to be able to check each step instead of just getting an answer. Claude showed the numbers for all three locations, and I reviewed the calculations to make sure everything was correct. It recommended Riverside Farmers Market because it fit the $5,000 budget and had the highest revenue minus rent. Its first response used emojis and Markdown formatting, so I asked for a plain version that ended with the exact Recommendation line, and the calculations stayed the same. I also noticed it used the word "profit" even though the numbers only subtract rent and don't include costs like beans or labor.

## Example Run

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

## Reflection

Comparing the four techniques, I think the examples made the biggest difference in getting Claude to match Wildframe's style. That was especially true for the customer replies in Task 3, where three examples gave it a clear sense of the tone. The one example in Task 2 was also enough for it to copy the bean card format. Chain-of-thought helped in a different way because Task 4 showed each calculation, which made the recommendation easier to review.

The main thing I learned is that following the format doesn't mean the answer is right. Claude left low acidity off the Cerrado card, and it made claims in the customer replies that weren't confirmed. Even after my follow-up, some of the replies still had promises I hadn't confirmed. Follow-up prompts helped, but I still had to read each response carefully.

I'm least sure about using zero-shot for Task 1. An example might have helped make the perks more realistic, but it also could have limited the creativity. I can't really say which would have worked better without trying it both ways.
