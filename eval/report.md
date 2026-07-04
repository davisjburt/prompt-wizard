# Prompt Wizard — Evaluation Report

- Date: 2026-07-04 17:10
- Grader model: `qwen2.5:7b-instruct` (self-grading — same model that writes the rewrites)
- Pairs: 10 (2 usage, 8 seed)
- **Average: 88% (B)**

## 1. Grade B (80%) — usage

Scores: intent=4, no_invention=5, clarity=4, structure=4, concise=3

**Issues:** The term 'LLM' could be expanded for clarity, and the first sentence is a bit redundant.

**Spoken:** This is my new app called prompt wizard so basically I think that it should be an app that will basically take what you say you can say it in just plain English and then it will format it into a prompt for an LLM that will specifically tell it the kind of work that you want to be done.

**Rewrite:**

```
This is my new app called Prompt Wizard. It should:
1. Take your spoken input, which you can provide in plain English.
2. Format it into a clear prompt for an LLM.
3. Specifically indicate the type of work you want to be done.
```

## 2. Grade B (80%) — seed

Scores: intent=4, no_invention=5, clarity=4, structure=3, concise=4

**Issues:** missing specification of the exact bug behavior

**Spoken:** uh okay so I want you to look at my python script and like there's this bug where when I pass in a list it sometimes crashes, I think it's something with empty lists maybe? fix it and also can you add some tests

**Rewrite:**

```
Review your Python script, fix the bug that causes it to crash when an empty list is passed in, and add tests.
```

## 3. Grade B (80%) — seed

Scores: intent=4, no_invention=5, clarity=4, structure=3, concise=4

**Issues:** Lacks a period at the end.

**Spoken:** okay can you um refactor the user service, it's gotten way too big, like split out the auth stuff into its own module and uh make sure the tests still pass, oh and don't change the public API because other teams use it

**Rewrite:**

```
Refactor the user service by splitting out the authentication stuff into its own module, ensure all tests still pass, and do not change the public API.
```

## 4. Grade B (80%) — seed

Scores: intent=4, no_invention=5, clarity=4, structure=3, concise=4

**Issues:** Missing 'timeout error' in the prompt; could be clearer about the exact nature of the failure.

**Spoken:** so the deploy failed again last night and the logs say something about a timeout connecting to redis, um can you look at the retry logic in the worker and figure out why it doesn't reconnect, maybe add some backoff

**Rewrite:**

```
Review the retry logic in the worker to determine why it doesn't reconnect after the timeout error when connecting to Redis. Add some backoff functionality if necessary.
```

## 5. Grade B (80%) — seed

Scores: intent=4, no_invention=5, clarity=4, structure=3, concise=4

**Issues:** Lacks a dash in the regex pattern, and 'major.dot.minor.patch[-prerelease]' is not clearly explained.

**Spoken:** hey I need a regex that matches like version strings you know the semver kind, major dot minor dot patch, and optionally a dash prerelease tag after, and can you explain it too because regex confuses me

**Rewrite:**

```
Write a regex that matches semantic version strings (major.dot.minor.patch[-prerelease]), and explain it in simple terms.
```

## 6. Grade A (92%) — seed

Scores: intent=4, no_invention=5, clarity=5, structure=5, concise=4

**Issues:** none

**Spoken:** write me a summary of this document but like keep it short, three bullets max, and make it something I could paste into Slack for my team, casual tone

**Rewrite:**

```
Write a summary of this document in no more than three bullets for a casual Slack message to your team.
```

## 7. Grade A (92%) — seed

Scores: intent=4, no_invention=5, clarity=5, structure=5, concise=4

**Issues:** Headline length requirement not explicitly stated in structure.

**Spoken:** make this landing page copy better, it's for a budgeting app aimed at college students, right now it sounds too corporate, I want it fun but still trustworthy, and keep the headline under ten words

**Rewrite:**

```
Rewrite the landing page copy to be fun yet trustworthy for a budgeting app targeted at college students. Keep the headline under ten words.
```

## 8. Grade A (100%) — usage

Scores: intent=5, no_invention=5, clarity=5, structure=5, concise=5

**Issues:** none

**Spoken:** Can you create an evaluator that will take all the prompts that get written based upon what I'm actually saying, take that, evaluate it, give it a grade, and then use that to iterate? You can use that same OLAMA LLM to grade as well.

**Rewrite:**

```
Create an evaluator that:
1. Takes all prompts generated based on your spoken input.
2. Evaluates each prompt.
3. Gives it a grade.
4. Uses the same OLAMA LLM for grading.

Iterate using the evaluation results.
```

## 9. Grade A (100%) — seed

Scores: intent=5, no_invention=5, clarity=5, structure=5, concise=5

**Issues:** none

**Spoken:** so basically I need an email to my landlord about the like broken heater it's been out for um three days now and I already texted him twice, keep it polite but firm and mention the lease says repairs happen within 48 hours

**Rewrite:**

```
Write an email to my landlord about the broken heater that has been out for three days, mentioning that I have already texted him twice. Keep the tone polite but firm, and include that the lease states repairs should be completed within 48 hours.
```

## 10. Grade A (100%) — seed

Scores: intent=5, no_invention=5, clarity=5, structure=5, concise=5

**Issues:** none

**Spoken:** I'm trying to decide between Postgres and Mongo for this new project, it's mostly relational data, users orders products that kind of thing, but some of it is like flexible metadata, give me a recommendation with reasons

**Rewrite:**

```
Recommend a database between Postgres and MongoDB for your new project, considering the data is mainly relational (users ordering products) but also includes flexible metadata. Provide reasons for your recommendation.
```
