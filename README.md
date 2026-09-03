# Klide - claude on kindle

## Idea

Use a kindle as an external display for claude.

Should support:
* streaming: high latency is ok, but the update should be continuous, no page reload or button press
* multiple conversations: jump between projects
* diff: see all the modified files, open to standard diff, from last commit is ok
* files: navigate and open

Nice to have:
* markdown rendering
* syntax highlighting
* minimal feedback: typing a full answer is out of scope, but a multiple choice or approval could be nice. opens a full can of worm about duplex connections or whatever, so maybe not.

Assumptions:
* Kindle can be fully hacked, preserving the existing OS is not a requirement. If so, being still able to read epubs is desirable, other formats not needed.
* Claude will always run on another machine.
* Kindle model is paperwhite 11th gen. Positive if more models are supported, but not a requirement.
* Updating firmware or whatever OS is in the kindle is not permitted, unless carefully vetted to prevent enshittification of the product. No amazon trash leaking into the kindle. No amazon account connected.
* If other Kindle models are more moddable, one could be purchased with limited budget.
