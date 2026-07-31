# Jacx Semantic Intelligence Evaluation Report

**Date**: 2026-07-31 15:27:00

**Commands Evaluated**: 1000

**Intelligence Score**: 84.3/100


## Accuracy Metrics

| Metric | Score |
|--------|-------|
| Intent Understanding | 78.7% |
| Planner Accuracy | 78.7% |
| Context Resolution | 95.0% |
| Memory Understanding | 100.0% |
| Query Extraction | 100.0% |
| Route Selection | 72.6% |
| Tool Selection | 72.6% |
| Clarification | 98.8% |
| **Overall Pipeline** | **65.7%** |

## Failure Analysis

| Category | Count | % | Root Cause | Suggested Improvement |
|----------|-------|---|------------|----------------------|
| Learning Intent Failures | 213 | 0.1% | Intent engine misclassifies the action family due to ambiguous or complex sentence structures | Expand action family patterns with more contextual signals and multi-word phrase detection |
| Routing Failures | 130 | 0.1% | Route selection logic doesn't match the intent to the correct handler | Improve route selection to consume StructuredIntent fields directly instead of raw text |

## Category Breakdown

| Category | Total | Correct | Accuracy |
|----------|-------|---------|----------|
| search | 203 | 66 | 32.5% |
| memory | 170 | 23 | 13.5% |
| learn | 153 | 38 | 24.8% |
| unknown | 108 | 8 | 7.4% |
| create | 70 | 15 | 21.4% |
| compare | 64 | 40 | 62.5% |
| ambiguous | 44 | 32 | 72.7% |
| recommend | 38 | 36 | 94.7% |
| open | 35 | 34 | 97.1% |
| reject | 33 | 8 | 24.2% |
| show | 32 | 4 | 12.5% |
| continue | 28 | 7 | 25.0% |
| approve | 14 | 12 | 85.7% |
| multi_step | 8 | 0 | 0.0% |

## Sample Commands Tested

```

[      memory] Discard my default news source preference
[   recommend] I'd like you to, propose something for Azure
[      create] I need you to write a code file
[      memory] Would you mind research AWS using my preferred browser
[     compare] Quantum computing vs Apache - which should I use
[      search] Tell me where to find React
[        open] Let's open terminal
[      search] I need to search blockchain on Opera
[      create] So, build a new image
[     compare] Is Vue better than Kafka
[  multi_step] Can you, first seek for Next.js, then how to about Kafka
[      memory] I usually use Celsius for temperature unit
[      reject] Stop remembering my default news source
[      create] Make a archive with Angular information
[      create] Compose a text file for JavaScript
[  multi_step] First I want to lookup biology, then learn about Flask
[    continue] Okay, keep going
[       learn] Describe philosophy in detail
[       learn] Why is Prometheus important
[     compare] Please, evaluate Azure and Vue
[   ambiguous] Do it again
[      reject] Cancel that
[   recommend] Any good options for Linux
[      memory] Toggle my preferred browser to C:\dev
[     unknown] I was working on something earlier
[      search] Tell me where to find physics
[      memory] So, store my project folder is my project folder
[   recommend] I need a good physics option
[       learn] I need info about neuroscience
[        open] Fire up calculator
[      create] I need you to build a video
[      search] Look into GraphQL
[      search] Google the web for CI/CD
[      memory] List my saved items
[      memory] Toggle the preferred browser setting
[      search] Where can I locate Go
[        open] I need to spin up Teams
[        open] So, open Teams
[    continue] I was wondering, carry on
[      search] So, lookup JavaScript, after that what are chemistry
[      memory] Can you change my theme to light theme
[       learn] Walk me through FastAPI
[    continue] Well, go on
[    continue] Let's pick up where we left off
[      search] Discover electric vehicles for me using my preferred browser
[       learn] I want a video covering AWS
[      create] Do me a favor, write a PDF about Kafka
[      search] I need to discover Nginx
[       learn] Teach me Linux
[      search] Browse Linux in Edge
```


## Intelligence Score Breakdown

- Intent Understanding (30%): 23.6/30
- Route Accuracy (20%): 14.5/20
- Query Extraction (15%): 15.0/15
- Memory Understanding (10%): 10.0/10
- Clarification (10%): 9.9/10
- Context Resolution (5%): 4.8/5
- Overall Pipeline (10%): 6.6/10

**Total: 84.3/100**
