
Problem Statement: Smart Financial Parser 💰
The Goal: Create a tool that ingests a "messy" dataset of financial transactions and
normalizes it into a clean report. This is a test of your ability to standardize unstructured data.
Your Task:
1. Create the Chaos (Data Setup): Create a dummy CSV file where the data is
inconsistent.
○ Dates: Mix formats (e.g., 2023-01-01, Jan 1st 23, 01/01/2023).
○ Merchants: Mix naming conventions (e.g., UBER *TRIP, Uber Technologies,
UBER EATS).
○ Amounts: Include currency symbols and inconsistent spacing.
2. Ingest & Normalize: Write code that ingests this dirty file and outputs a clean,
standardized list. Note: We expect you to use libraries or AI techniques to handle this
normalization efficiently.
3. Analysis: Once cleaned, output a report flagging the top spending category.
What We Look For:
● Leverage: Did you write 50 manual if/else statements (inefficient), or did you use a
library/AI workflow to normalize the data (efficient)?
● Robustness: Does your code crash on a date format it hasn't seen before, or does it
handle it gracefully?
● Evidence: Did you include a "messy" sample CSV that actually triggers the
inconsistencies, proving your normalizer works?

Case Challenge: How You'll Be Scored
● Learning Continuously: Learning faster than the landscape shifts by experimenting with
new approaches (AI/Libraries) to enhance performance.
● Adapting: Shifting strategies in response to "messy" data constraints. Diagnosing the
underlying need (e.g., accurate timezone handling) rather than just the stated task.
● Creativity: Your originality, practicality, and forward-thinking in designing the solution.
● Debugging Code: Diagnosing defects and applying safeguards. Verifying accuracy,
latency, and correctness of the system.
● Developing Maintainable Code: Focusing on all aspects to ensure quality and accuracy.
Verifying outputs from automation/AI to ensure security and maintainability.
● Communicating & Presenting: Clearly and transparently conveying information.
Explaining technical choices and trade-offs.


The Rules of Engagement
1. Code Over Concept: We are evaluating your technical execution, not your product
management skills. A simple, working command-line interface (CLI) with clean code and 100%
test coverage is better than a broken web app with beautiful buttons. Focus on the logic.
2. AI Usage Disclosure: We embrace modern tools, including AI (ChatGPT, Copilot, etc.).
However, you must own your solution.
● Transparency: If you use AI (ChatGPT, Copilot, etc.) to generate code, you must
disclose it
● Validation: You are responsible for every line of code. If an AI tool introduces a bug or
a security flaw, that is your responsibility to catch.
● Documentation: Your submission must include a "Methodology" section in your
README explaining which tools you used and how you verified their output.
3. The README is Your Voice: Since you won't be presenting this live, your README.md file
is the most important part of your submission after the code itself.
● Don't just say: "Run main.py."
● Do say: ""I chose to use the pandas library here because raw CSV parsing is brittle..."
or "I prompted ChatGPT to generate the regex for the date formats, but verified it
against these three edge cases..."


Evaluation Criteria:
Your submission will be evaluated on Engineering Integrity (clean logic, readable code). Please adhere to these essential requirements:

I. Code & Execution
Select One Challenge: Choose and solve ONE of the three case study options.

Deliver a CLI: The solution must be a functional Command-Line Interface (CLI).

Focus: Prioritize clean logic and readable code over a "flashy" interface.

Leverage Tools: Use libraries or AI tools for efficiency when appropriate, as we value robust solutions delivered quickly.

II. Documentation & Integrity
Crucial README.md: The README.md file is the most important part of your submission after the code, as there is no live presentation.

Explain Choices: Use the README.md to explain your technical rationale (e.g., why you chose a specific library).

Mandatory AI Disclosure: If you use AI (e.g., ChatGPT, Copilot), you must disclose it.

"Methodology" Section: Include a dedicated "Methodology" section in your README detailing the tools used and how you verified their output.

Own the Code: You are fully responsible for every line of code; any AI-introduced bugs or security flaws are your responsibility to catch.